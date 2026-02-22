import os
import json
import glob
from typing import List, Dict, Any
import re

from prefect import flow, task
from loguru import logger

from src.adapters.sources.lattes_parser import LattesParser
from src.core.logic.entity_manager import EntityManager
from eo_lib import InitiativeController, PersonController, TeamController
from research_domain.controllers import (
    ResearcherController,
    AcademicEducationController,
    ArticleController
)
from research_domain.domain.entities.academic_education import AcademicEducation, EducationType, academic_education_knowledge_areas
from research_domain.domain.entities.researcher import Researcher
from research_domain.domain.entities.article import Article, article_authors

from src.core.logic.project_loader import ProjectLoader
from src.core.logic.strategies.lattes_projects import LattesProjectMappingStrategy

from prefect.cache_policies import NO_CACHE

@task(name="Ingest Lattes Researcher Data", cache_policy=NO_CACHE)
def ingest_researcher_data(file_path: str, entity_manager: EntityManager, parser: LattesParser):
    try:
        filename = os.path.basename(file_path)
        lattes_id = filename.replace(".json", "").split("_")[-1]

        if not lattes_id or not lattes_id.isdigit():
            logger.warning(f"Skipping file {filename}: Could not extract Lattes ID.")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON {file_path}: {e}")
            return
            
        json_name = data.get("nome") or data.get("name")
        if not json_name:
            info = data.get("informacoes_pessoais", {})
            json_name = info.get("nome_completo")

        researcher_ctrl = ResearcherController()
        all_researchers = researcher_ctrl.get_all()
        target_researcher = next((r for r in all_researchers if str(getattr(r, "brand_id", "") or "") == lattes_id), None)

        if not target_researcher and json_name:
            logger.info(f"ID {lattes_id} match failed. Trying name from JSON: {json_name}")
            target_researcher = next((r for r in all_researchers if getattr(r, "name", "").lower() == json_name.lower()), None)
            
        if not target_researcher:
            logger.warning(f"Researcher with lattes_id {lattes_id} not found in DB and Name match failed. Skipping file {filename}.")
            return
            
        # 1. Update Personal Info
        personal_info = parser.parse_personal_info(data)
        needs_update = False
        if personal_info.get("citation_names"):
            target_researcher.citation_names = personal_info["citation_names"]
            needs_update = True
        if personal_info.get("cnpq_url"):
            target_researcher.cnpq_url = personal_info["cnpq_url"]
            needs_update = True
        if personal_info.get("resume"):
            target_researcher.resume = personal_info["resume"]
            needs_update = True
            
        if needs_update:
            try:
                researcher_ctrl.update(target_researcher)
            except Exception as e:
                logger.warning(f"Failed to update researcher data for {lattes_id}: {e}")

        logger.info(f"Processing data for researcher: {target_researcher.name} (Lattes: {lattes_id})")

        # 2. Extract Projects
        projects = []
        projects.extend(parser.parse_research_projects(data))
        projects.extend(parser.parse_extension_projects(data))
        projects.extend(parser.parse_development_projects(data))
        
        # Deduplicate projects by name
        seen_names = set()
        unique_projects = []
        for p in projects:
            p_name = (p.get("name") or "").strip()
            if p_name and p_name not in seen_names:
                p["name"] = p_name
                unique_projects.append(p)
                seen_names.add(p_name)

        if unique_projects:
            logger.info(f"Ingesting {len(unique_projects)} projects with ProjectLoader for {target_researcher.name}")
            # Identify researcher roles prior to loading
            researcher_roles = {p["name"]: p.get("role") for p in unique_projects}
            
            mapping_strategy = LattesProjectMappingStrategy(target_researcher.name, researcher_roles)
            loader = ProjectLoader(mapping_strategy=mapping_strategy)
            
            loader.process_records(unique_projects)

        # 3. Handle Articles
        articles = []
        articles.extend(parser.parse_articles(data))
        articles.extend(parser.parse_conference_papers(data))
        if articles:
            ingest_articles_task(articles, target_researcher, all_researchers, parser)

        # 4. Handle Academic Education
        education_list = parser.parse_academic_education(data)
        if education_list:
            ingest_education_task(education_list, target_researcher, all_researchers, entity_manager, researcher_ctrl)

    except Exception as e:
        logger.error(f"Failed to process file {file_path}: {e}")


def ingest_articles_task(articles: List[Dict], target_researcher: Researcher, all_researchers: List[Researcher], parser: LattesParser):
    logger.info(f"Processing {len(articles)} articles for {target_researcher.name}...")
    article_ctrl = ArticleController()
    
    try:
        all_db_articles = article_ctrl.get_all()
        doi_map = {a.doi: a for a in all_db_articles if getattr(a, "doi", None)}
        
        def get_art_key(title, year):
            norm_t = parser.normalize_title(title)
            return f"{norm_t}_{year}"
        
        title_year_map = {get_art_key(a.title, a.year): a for a in all_db_articles}
    except Exception as cache_err:
        logger.warning(f"Failed to build article lookup cache: {cache_err}")
        doi_map = {}
        title_year_map = {}

    for art in articles:
        try:
            title = art["title"]
            year = art["year"]
            doi = art.get("doi")
            
            existing_art = None
            if doi and doi in doi_map:
                existing_art = doi_map[doi]
            if not existing_art:
                art_key = get_art_key(title, year)
                if art_key in title_year_map:
                    existing_art = title_year_map[art_key]

            if existing_art:
                paper = existing_art
            else:
                paper = article_ctrl.create_article(
                    title=title,
                    year=year,
                    type=art["type"],
                    doi=doi,
                    journal_conference=art.get("journal_conference"),
                    volume=art.get("volume"),
                    pages=art.get("pages")
                )
                if doi:
                    doi_map[doi] = paper
                title_year_map[get_art_key(title, year)] = paper

            # Link primary author
            current_author_ids = [getattr(auth, "id") for auth in getattr(paper, "authors", [])]
            if target_researcher.id not in current_author_ids:
                try:
                    article_ctrl.add_author(paper.id, target_researcher.id)
                except Exception as link_err:
                    pass

        except Exception as art_err:
            logger.error(f"Failed to ingest article {art.get('title')}: {art_err}")


def ingest_education_task(education_list: List[Dict], target_researcher: Researcher, all_researchers: List[Researcher], entity_manager: EntityManager, researcher_ctrl: ResearcherController):
    logger.info(f"Processing {len(education_list)} education entries for {target_researcher.name}...")
    
    for edu_data in education_list:
        try:
            inst_name = edu_data.get("institution") or "Unknown Institution"
            org_id = entity_manager.ensure_organization(name=inst_name)
            if not org_id:
                continue

            type_name = edu_data.get("degree") or "Unknown"
            type_id = entity_manager.ensure_education_type(name=type_name)
            if not type_id:
                 continue

            advisor_id = None
            co_advisor_id = None
            description = edu_data.get("description", "")
            
            if description:
                adv_match = re.search(r"Orientador:\s*([^.;)]+)", description, re.IGNORECASE)
                if adv_match:
                    adv_name = adv_match.group(1).strip()
                    adv_res = next((r for r in all_researchers if getattr(r, "name", "").lower() == adv_name.lower()), None)
                    if adv_res:
                        advisor_id = getattr(adv_res, "id")
                    else:
                        try:
                            new_adv = Researcher(name=adv_name)
                            researcher_ctrl.create(new_adv)
                            advisor_id = getattr(new_adv, "id")
                            all_researchers.append(new_adv)
                        except Exception:
                            pass

                co_match = re.search(r"Co-?orientador:\s*([^.;)]+)", description, re.IGNORECASE)
                if co_match:
                    co_name = co_match.group(1).strip()
                    co_res = next((r for r in all_researchers if getattr(r, "name", "").lower() == co_name.lower()), None)
                    if co_res:
                        co_advisor_id = getattr(co_res, "id")
                    else:
                        try:
                            new_co = Researcher(name=co_name)
                            researcher_ctrl.create(new_co)
                            co_advisor_id = getattr(new_co, "id")
                            all_researchers.append(new_co)
                        except Exception:
                            pass

            start_val = edu_data.get("start_year") or 0
            
            entity_manager.academic_edu_controller.create_academic_education(
                researcher_id=target_researcher.id,
                education_type_id=type_id,
                title=edu_data.get("course_name") or "Untitled",
                institution_id=org_id,
                start_year=start_val,
                end_year=edu_data.get("end_year"),
                thesis_title=edu_data.get("thesis_title"),
                advisor_id=advisor_id,
                co_advisor_id=co_advisor_id
            )
        except Exception as e:
            logger.warning(f"Failed to ingest education item: {e}")


@flow(name="Ingest Lattes Projects Flow")
def ingest_lattes_projects_flow():
    base_dir = "data/lattes_json"
    if not os.path.isabs(base_dir):
        base_dir = os.path.join(os.getcwd(), base_dir)
        
    json_files = glob.glob(os.path.join(base_dir, "*.json"))
    logger.info(f"Found {len(json_files)} files in {base_dir}")
    
    if not json_files:
        return

    init_ctrl = InitiativeController()
    person_ctrl = PersonController()
    entity_manager = EntityManager(init_ctrl, person_ctrl)
    parser = LattesParser()
    
    try:
        from eo_lib.domain.base import Base
        engine = init_ctrl.client.engine if hasattr(init_ctrl, 'client') else None
        if not engine:
             from eo_lib.infrastructure.database.postgres_client import PostgresClient
             repo = PostgresClient()
             engine = repo.engine
        
        try:
             AcademicEducation.__table__.drop(engine, checkfirst=True)
             academic_education_knowledge_areas.drop(engine, checkfirst=True)
             EducationType.__table__.drop(engine, checkfirst=True)
             Article.__table__.drop(engine, checkfirst=True)
             article_authors.drop(engine, checkfirst=True)
        except Exception:
             pass

        Base.metadata.create_all(engine)
    except Exception as e:
        logger.warning(f"Could not ensure table creation: {e}")

    for json_file in json_files:
        ingest_researcher_data(json_file, entity_manager, parser)

if __name__ == "__main__":
    ingest_lattes_projects_flow()

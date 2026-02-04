import os
import json
import glob
from datetime import datetime, date
from typing import List

from prefect import flow, task
from loguru import logger

from src.adapters.sources.lattes_parser import LattesParser
from src.core.logic.entity_manager import EntityManager
from eo_lib import Initiative, InitiativeController, PersonController, TeamController
from research_domain.controllers import (
    ResearcherController,
    AcademicEducationController,
    ArticleController
)
from research_domain.domain.entities.academic_education import AcademicEducation, EducationType, academic_education_knowledge_areas
from research_domain.domain.entities.researcher import Researcher

from prefect.cache_policies import NO_CACHE

@task(name="Ingest Lattes Projects for File", cache_policy=NO_CACHE)
def ingest_file_task(file_path: str, entity_manager: EntityManager):
    try:
        # Extract Lattes ID from filename
        # Format: 00_Name_LattesID.json OR just LattesID.json (mock)
        filename = os.path.basename(file_path)
        lattes_id = filename.replace(".json", "").split("_")[-1]

        if not lattes_id or not lattes_id.isdigit():
            logger.warning(f"Skipping file {filename}: Could not extract Lattes ID.")
            return

        # Load JSON first to get Name if needed
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON {file_path}: {e}")
            return
            
        # Try to get name from root or informacoes_pessoais
        json_name = data.get("nome") or data.get("name")
        if not json_name:
            info = data.get("informacoes_pessoais", {})
            json_name = info.get("nome_completo")

        # Find Researcher
        researcher_ctrl = ResearcherController()
        # Optimization: We can cache researchers map if this is slow.
        all_researchers = researcher_ctrl.get_all()
        target_researcher = next((r for r in all_researchers if str(getattr(r, "brand_id", "") or "") == lattes_id), None)

        if not target_researcher and json_name:
            # Fallback: Try to match by Name from JSON
            logger.info(f"ID {lattes_id} match failed. Trying name from JSON: {json_name}")
            target_researcher = next((r for r in all_researchers if getattr(r, "name", "").lower() == json_name.lower()), None)
            
            if target_researcher:
                logger.info(f"Matched researcher by name: {json_name} (ID: {getattr(target_researcher, 'id', 'N/A')})")

        if not target_researcher:
            logger.warning(f"Researcher with lattes_id {lattes_id} not found in DB and Name match failed. Skipping projects for {filename}.")
            return
        
        # Parse Personal Info
        parser = LattesParser()
        personal_info = parser.parse_personal_info(data)
        
        # Update Researcher Details (Citation Names, CNPq URL, Resume)
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
                logger.info(f"Updated researcher data (Resume/Citation/URL) for {json_name}")
            except Exception as e:
                logger.warning(f"Failed to update researcher data for {lattes_id}: {e}")

        # Parse Projects
        projects = []
        projects.extend(parser.parse_research_projects(data))
        projects.extend(parser.parse_extension_projects(data))
        projects.extend(parser.parse_development_projects(data))

        if not projects:
            logger.info(f"No projects found for {filename}.")
        else:
            logger.info(f"Found {len(projects)} projects for {lattes_id}.")

        # Parse Articles
        articles = []
        articles.extend(parser.parse_articles(data))
        articles.extend(parser.parse_conference_papers(data))
        
        if not articles:
            logger.info(f"No articles found for {filename}.")
        else:
            logger.info(f"Found {len(articles)} articles for {lattes_id}.")

        # Parse Academic Education
        education_list = parser.parse_academic_education(data)
        logger.info(f"Found {len(education_list)} education entries for {lattes_id}.")

        # Ingest Projects
        initiative_ctrl = InitiativeController()
        team_ctrl = TeamController()
        article_ctrl = ArticleController()
        
        # Ensure Types
        types_map = {
            "Research Project": entity_manager.ensure_initiative_type("Research Project"),
            "Extension Project": entity_manager.ensure_initiative_type("Extension Project"),
            "Development Project": entity_manager.ensure_initiative_type("Development Project")
        }

        # Ensure Organization (IFES)
        org_id = entity_manager.ensure_organization()

        # Deduplicate projects by name in-memory to avoid batch conflicts
        seen_names = set()
        unique_projects = []
        for p in projects:
            p_name = (p.get("name") or "").strip()
            if p_name and p_name not in seen_names:
                p["name"] = p_name # Normalize
                unique_projects.append(p)
                seen_names.add(p_name)
        
        logger.info(f"deduplicated from {len(projects)} to {len(unique_projects)} projects.")

        from eo_lib.infrastructure.database.postgres_client import PostgresClient
        db_client = PostgresClient()
        db_session = db_client.get_session()

        # Prepare Roles Cache
        roles_cache = entity_manager.ensure_roles()

        for p in unique_projects:
            try:
                p_type = types_map.get(p["initiative_type_name"])
                
                # Fallback for Development Project if not found (Double Check)
                if not p_type and p["initiative_type_name"] == "Development Project":
                    try:
                         # Force ensure
                         p_type = entity_manager.ensure_initiative_type("Development Project")
                         types_map["Development Project"] = p_type
                         logger.info("Force-created 'Development Project' type during ingestion loop.")
                    except Exception as err:
                         logger.error(f"Failed to fallback create Development Project type: {err}")

                type_id = getattr(p_type, "id", None)

                # Check if exists (Idempotency)
                from sqlalchemy import text
                
                init_id = None
                # Check by name constraint using robust query
                chk_sql = text("SELECT id FROM initiatives WHERE LOWER(name) = LOWER(:name) LIMIT 1")
                res = db_session.execute(chk_sql, {"name": p["name"]}).fetchone()
                if res:
                        init_id = res[0]
                        logger.info(f"Skipping creation, Initiative exists: {p['name']} (ID: {init_id})")

                # Create Mapping Start/End Dates
                start_date = None
                if p["start_year"]:
                    try:
                        start_date = datetime.strptime(f"{p['start_year']}-01-01", "%Y-%m-%d")
                    except ValueError:
                        start_date = None
                
                end_date = None
                if p["end_year"]:
                    try:
                         end_date = datetime.strptime(f"{p['end_year']}-12-31", "%Y-%m-%d")
                    except ValueError:
                         end_date = None

                if not init_id:
                     # Create Initiative Object
                     new_init = Initiative(
                         name=p["name"],
                         description=p["description"],
                         start_date=start_date,
                         end_date=end_date,
                         status=p["status"],
                         initiative_type_id=type_id,
                         organization_id=org_id
                     )
                     
                     initiative_ctrl.create(new_init)
                     init_id = getattr(new_init, "id", None)

                # Process Sponsors (Financiadores)
                if init_id:
                     raw_sponsors = p.get("raw_sponsors", [])
                     if raw_sponsors:
                         # Pick the first one as demandante for now
                         sponsor_name = raw_sponsors[0].get("nome")
                         if sponsor_name:
                             sponsor_org_id = entity_manager.ensure_organization(name=sponsor_name)
                             if sponsor_org_id:
                                 # We need to link it. If using controller, we might need a direct update or service call.
                                 # For simplicity, we'll use the initiative object if we can or direct SQL if needed.
                                 # Let's try to get the initiative object
                                 try:
                                     init_obj = initiative_ctrl.get_by_id(init_id)
                                     if init_obj and not getattr(init_obj, "demandante", None):
                                         sponsor_org = entity_manager.get_organization(sponsor_org_id)
                                         if sponsor_org:
                                             init_obj.demandante = sponsor_org
                                             initiative_ctrl.update(init_obj)
                                             logger.info(f"Assigned sponsor {sponsor_name} as demandante for {p['name']}")
                                 except Exception as sponsor_err:
                                     logger.warning(f"Failed to assign sponsor for {init_id}: {sponsor_err}")

                # Resolve/Get Team ID
                target_team_id = None
                try:
                     teams = initiative_ctrl.get_teams(init_id)
                     if teams:
                         target_team_id = teams[0].get("id") if isinstance(teams[0], dict) else getattr(teams[0], "id")
                     else:
                         # Create a team for this initiative if none exists
                         team_name = f"Team: {p['name']}"[:100]
                         logger.info(f"Creating team '{team_name}' for initiative {init_id}")
                         new_team = team_ctrl.create_team(name=team_name, description=f"Team for {p['name']}")
                         target_team_id = getattr(new_team, "id")
                         initiative_ctrl.assign_team(init_id, target_team_id)
                except Exception as team_err:
                     logger.warning(f"Failed to ensure team for initiative {init_id}: {team_err}")
                
                # Add Researcher as Coordinator/Member
                person_id = getattr(target_researcher, "id", None)
                if init_id and person_id and target_team_id:
                    try:
                        # Check if already in team
                        current_members = team_ctrl.get_members(target_team_id)
                        is_member = any(m.person_id == person_id for m in current_members)
                        
                        if not is_member:
                            # Map papel to role
                            # Find the main researcher in the members list to get their role
                            raw_members = p.get("raw_members", [])
                            researcher_role = "Integrante" # Default
                            for rm in raw_members:
                                if parser.normalize_title(rm.get("nome", "")) == parser.normalize_title(target_researcher.name):
                                    researcher_role = rm.get("papel", "Integrante")
                                    break

                            m_role_name = "Coordinator" if researcher_role == "Coordenador" else "Researcher"
                            m_role = roles_cache.get(m_role_name)
                            
                            team_ctrl.add_member(target_team_id, person_id, m_role)
                            logger.info(f"Linked researcher {target_researcher.name} as {m_role_name} to {p['name']}")
                    except Exception as e:
                        logger.warning(f"Failed to link researcher to project {p['name']}: {e}")

                # Process Other Members (Equipe)
                if init_id and target_team_id:
                     raw_members = p.get("raw_members", [])
                     
                     try:
                         current_members = team_ctrl.get_members(target_team_id)
                         
                         for m in raw_members:
                             m_name = m.get("nome")
                             m_role_raw = m.get("papel", "Integrante")
                             
                             if not m_name or m_name == target_researcher.name:
                                 continue
                                 
                             # Resolve Person by Name
                             m_name_norm = parser.normalize_title(m_name)
                             found_person = next(
                                 (r for r in all_researchers if parser.normalize_title(getattr(r, "name", "")) == m_name_norm), 
                                 None
                             )
                             
                             if found_person:
                                 m_person_id = getattr(found_person, "id")
                                 
                                 # Map Role
                                 role_key = "Researcher" # Default
                                 if "coordenador" in m_role_raw.lower():
                                     role_key = "Coordinator"
                                 elif "estudante" in m_role_raw.lower() or "bolsista" in m_role_raw.lower():
                                     role_key = "Student"
                                 
                                 m_role = roles_cache.get(role_key)
                                 
                                 # Add Member
                                 try:
                                     # Check if already member
                                     is_member = any(mm.person_id == m_person_id for mm in current_members)
                                     if not is_member:
                                         team_ctrl.add_member(
                                             team_id=target_team_id,
                                             person_id=m_person_id,
                                             role=m_role,
                                             start_date=start_date,
                                             end_date=end_date
                                         )
                                         logger.info(f"Added member {m_name} as {role_key} to {p['name']}")
                                 except Exception as mem_err:
                                     pass
                     except Exception as team_err:
                         logger.warning(f"Failed to process team members for initiative {init_id}: {team_err}")

            except Exception as e:
                logger.error(f"Error creating project {p['name']}: {e}")
                # Important: Rollback session to clear error state for next iterations
                if db_session:
                    try:
                        db_session.rollback()
                        logger.info("Session rolled back after error.")
                    except Exception as rb_err:
                         logger.error(f"Failed to rollback: {rb_err}")
            
        # Commit all projects and articles for this researcher
        if db_session:
            try:
                db_session.commit()
                logger.debug(f"Committed data for {json_name}")
            except Exception as commit_err:
                logger.error(f"Failed to commit data for {json_name}: {commit_err}")

        # Ingest Articles
        # Optimization: Pre-load articles if many are expected, but here we use a local cache for the run
        # To be truly efficient, we should load once per flow, but for now let's optimize the per-researcher loop
        
        logger.info(f"Processing {len(articles)} articles for {json_name}...")
        
        # Load all existing articles once per researcher to avoid N calls to get_all()
        # Better: Load once in the flow and pass it, but per-researcher get_all() is still better than per-article
        try:
            all_db_articles = article_ctrl.get_all()
            # Create indices for fast lookup
            doi_map = {a.doi: a for a in all_db_articles if getattr(a, "doi", None)}
            
            def get_art_key(title, year):
                norm_t = parser.normalize_title(title)
                return f"{norm_t}_{year}"
            
            title_year_map = {get_art_key(a.title, a.year): a for a in all_db_articles}
        except Exception as cache_err:
            logger.warning(f"Failed to build article lookup cache: {cache_err}. Falling back to slow lookup.")
            doi_map = {}
            title_year_map = {}

        for art in articles:
            try:
                title = art["title"]
                year = art["year"]
                doi = art.get("doi")
                
                existing_art = None
                
                # 1. Check by DOI
                if doi and doi in doi_map:
                    existing_art = doi_map[doi]
                    logger.debug(f"Article matched by DOI: {doi}")
                
                # 2. Check by Title + Year (Normalized)
                if not existing_art:
                    art_key = get_art_key(title, year)
                    if art_key in title_year_map:
                        existing_art = title_year_map[art_key]
                        logger.debug(f"Article matched by Title/Year: {art_key}")

                if existing_art:
                    paper = existing_art
                else:
                    # Create Article
                    paper = article_ctrl.create_article(
                        title=title,
                        year=year,
                        type=art["type"],
                        doi=doi,
                        journal_conference=art.get("journal_conference"),
                        volume=art.get("volume"),
                        pages=art.get("pages")
                    )
                    logger.info(f"Created new article: {title} ({art['type']})")
                    
                    # Update cache to prevent duplicates within the same researcher loop
                    if doi:
                        doi_map[doi] = paper
                    title_year_map[get_art_key(title, year)] = paper

                # Link Author (Target Researcher)
                if paper and target_researcher:
                    # Use author IDs to check existence
                    current_author_ids = [getattr(auth, "id") for auth in getattr(paper, "authors", [])]
                    if target_researcher.id not in current_author_ids:
                        try:
                            article_ctrl.add_author(paper.id, target_researcher.id)
                            logger.debug(f"Linked author {target_researcher.name} to article {paper.id}")
                        except Exception as link_err:
                            logger.warning(f"Failed to link author {target_researcher.name} to article {paper.id}: {link_err}")

            except Exception as art_err:
                logger.error(f"Failed to ingest article {art.get('title')}: {art_err}")

        # Ingest Academic Education
        if education_list:
            for edu_data in education_list:
                try:
                    # 1. Organization (Institution) - MANDATORY
                    inst_name = edu_data.get("institution") or "Unknown Institution"
                    org_id = entity_manager.ensure_organization(name=inst_name)
                    if not org_id:
                        logger.warning(f"Skipping Education: Could not resolve organization for {inst_name}")
                        continue

                    # 2. Education Type - MANDATORY
                    type_name = edu_data.get("degree") or "Unknown"
                    type_id = entity_manager.ensure_education_type(name=type_name)
                    if not type_id:
                         logger.warning(f"Skipping Education: Could not resolve type {type_name}")
                         continue

                    # 3. Advisor Lookup (Optional)
                    advisor_id = None
                    co_advisor_id = None
                    description = edu_data.get("description", "")
                    
                    if description:
                        import re
                        # Advisor Parser
                        adv_match = re.search(r"Orientador:\s*([^.;)]+)", description, re.IGNORECASE)
                        if adv_match:
                            adv_name = adv_match.group(1).strip()
                            adv_res = next((r for r in all_researchers if getattr(r, "name", "").lower() == adv_name.lower()), None)
                            if adv_res:
                                advisor_id = getattr(adv_res, "id")
                            else:
                                # Create Stub Researcher
                                logger.info(f"Creating Stub Researcher for Advisor: {adv_name}")
                                try:
                                    new_adv = Researcher(name=adv_name)
                                    researcher_ctrl.create(new_adv)
                                    advisor_id = getattr(new_adv, "id")
                                    # Add to cache to avoid re-creation in same run
                                    all_researchers.append(new_adv)
                                except Exception as e:
                                    logger.warning(f"Failed to create stub advisor {adv_name}: {e}")

                        # Co-Advisor Parser
                        co_match = re.search(r"Co-?orientador:\s*([^.;)]+)", description, re.IGNORECASE)
                        if co_match:
                            co_name = co_match.group(1).strip()
                            co_res = next((r for r in all_researchers if getattr(r, "name", "").lower() == co_name.lower()), None)
                            if co_res:
                                co_advisor_id = getattr(co_res, "id")
                            else:
                                # Create Stub Researcher
                                logger.info(f"Creating Stub Researcher for Co-Advisor: {co_name}")
                                try:
                                    new_co = Researcher(name=co_name)
                                    researcher_ctrl.create(new_co)
                                    co_advisor_id = getattr(new_co, "id")
                                    all_researchers.append(new_co)
                                except Exception as e:
                                    logger.warning(f"Failed to create stub co-advisor {co_name}: {e}")

                    # 4. Create Entity via Controller
                    start_val = edu_data.get("start_year")
                    if start_val is None: start_val = 0
                    
                    entity_manager.academic_edu_controller.create_academic_education(
                        researcher_id=person_id,
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
                    logger.warning(f"Failed to ingest education item for {lattes_id}: {e}")

    except Exception as e:
        logger.error(f"Failed to process file {file_path}: {e}")

@flow(name="Ingest Lattes Projects Flow")
def ingest_lattes_projects_flow():
    base_dir = "data/lattes_json"
    # Ensure absolute path
    if not os.path.isabs(base_dir):
        base_dir = os.path.join(os.getcwd(), base_dir)
        
    logger.info(f"Looking for JSONs in: {base_dir}")
    logger.info(f"CWD: {os.getcwd()}")
    
    json_files = glob.glob(os.path.join(base_dir, "*.json"))
    logger.info(f"Found {len(json_files)} files.")
    
    if not json_files:
        logger.warning(f"No JSON files found in {base_dir}")
        logger.info(f"Directory listing: {os.listdir(base_dir) if os.path.exists(base_dir) else 'Dir not found'}")
        return

    # Setup Managers
    init_ctrl = InitiativeController()
    person_ctrl = PersonController()
    entity_manager = EntityManager(init_ctrl, person_ctrl)
    
    # Ensure AcademicEducation table exists
    # This is a temporary fix for local entity support
    try:
        from eo_lib.domain.base import Base
        from research_domain.domain.entities.academic_education import AcademicEducation
        from research_domain.domain.entities.article import Article, article_authors
        # Get engine from one of the controllers or client
        engine = init_ctrl.client.engine if hasattr(init_ctrl, 'client') else None
        if not engine:
             # Fallback
             from eo_lib.infrastructure.database.postgres_client import PostgresClient
             repo = PostgresClient()
             engine = repo.engine
        
             repo = PostgresClient()
             engine = repo.engine
        
        # Dev: Drop table to ensure schema update
        try:
             # Check if we should drop - useful for dev iterations
             AcademicEducation.__table__.drop(engine, checkfirst=True)
             academic_education_knowledge_areas.drop(engine, checkfirst=True)
             EducationType.__table__.drop(engine, checkfirst=True)
             
             Article.__table__.drop(engine, checkfirst=True)
             article_authors.drop(engine, checkfirst=True)
             
             logger.warning("Dropped academic and publication tables for schema update.")
        except Exception as drop_err:
             logger.warning(f"Failed to drop table: {drop_err}")

        Base.metadata.create_all(engine)
        logger.info("Ensured AcademicEducation table exists.")
    except Exception as e:
        logger.warning(f"Could not ensure table creation: {e}")

    # Run Tasks
    for json_file in json_files:
        ingest_file_task(json_file, entity_manager)

if __name__ == "__main__":
    ingest_lattes_projects_flow()

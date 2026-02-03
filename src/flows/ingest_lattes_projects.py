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
from research_domain import ResearcherController
from src.core.controllers.academic_education_controller import AcademicEducationController
from src.core.domain.academic_education import AcademicEducation, academic_education_knowledge_areas
from src.core.domain.education_type import EducationType

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

        person_id = getattr(target_researcher, "id", None)
        if not person_id:
             logger.warning(f"Researcher {target_researcher} has no ID.")
             return

        # Parse Projects
        parser = LattesParser()
        projects = []
        projects.extend(parser.parse_research_projects(data))
        projects.extend(parser.parse_extension_projects(data))
        projects.extend(parser.parse_development_projects(data))

        if not projects:
            logger.info(f"No projects found for {filename}.")
        else:
            logger.info(f"Found {len(projects)} projects for {lattes_id}.")

        # Parse Academic Education
        education_list = parser.parse_academic_education(data)
        logger.info(f"Found {len(education_list)} education entries for {lattes_id}.")

        # Ingest Projects
        initiative_ctrl = InitiativeController()
        team_ctrl = TeamController()
        
        # Ensure Types
        types_map = {
            "Research Project": entity_manager.ensure_initiative_type("Research Project"),
            "Extension Project": entity_manager.ensure_initiative_type("Extension Project"),
            "Development Project": entity_manager.ensure_initiative_type("Development Project")
        }

        # Ensure Organization (IFES)
        org_id = entity_manager.ensure_organization()

        for p in projects:
            try:
                p_type = types_map.get(p["initiative_type_name"])
                type_id = getattr(p_type, "id", None)

                # Check if exists (Idempotency)
                from sqlalchemy import text
                
                # Get session access
                session_chk = None
                if hasattr(initiative_ctrl, "_session") and initiative_ctrl._session:
                     session_chk = initiative_ctrl._session
                elif hasattr(initiative_ctrl, "client"):
                     session_chk = initiative_ctrl.client.get_session()
                
                init_id = None
                if session_chk:
                    # Check by name constraint
                    chk_sql = text("SELECT id FROM initiatives WHERE name = :name LIMIT 1")
                    res = session_chk.execute(chk_sql, {"name": p["name"]}).fetchone()
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
                
                # Add Researcher as Coordinator/Member
                if init_id and person_id:
                    role_name = "Researcher" # Default
                    role = entity_manager.ensure_roles().get(role_name)
                    role_id = getattr(role, "id", None)
                    
                    if role_id:
                        try:
                            team_ctrl.add_member(
                                team_id=init_id,
                                person_id=person_id,
                                role_id=role_id,
                                start_date=start_date, # Use project dates as membership dates for simplicity
                                end_date=end_date
                            )
                        except Exception as e:
                            # It might be that we need to create a Team first, or the Initiative ID != Team ID.
                            # Also handle duplicates if already member
                            pass
                
                 # Process Other Members (Equipe)
                raw_members = p.get("raw_members", [])
                
                # Fetch team mapping for this initiative
                # Initiative -> [Teams]
                # We assume the first team is the main team for the project
                try:
                     teams = initiative_ctrl.get_teams(init_id)
                     if teams:
                         target_team_id = teams[0].get("id") if isinstance(teams[0], dict) else getattr(teams[0], "id")
                         
                         for member in raw_members:
                             m_name = member.get("nome") or member.get("name")
                             m_role_str = member.get("papel", "Integrante")
                             
                             if not m_name: 
                                 continue
                                 
                             # Resolve Person by Name
                             # We need a way to find person by name. 
                             # distinct names search?
                             # For now, let's try to find in `all_researchers` cache or skip if not simple.
                             # But `all_researchers` only has researchers. Students might not be there.
                             # If person_ctrl has `get_by_name`, great.
                             # If not, we might be unable to link without creating new Persons.
                             # For this task, we will try to link EXISTING researchers/people.
                             
                             # Simple fuzzy logic or exact match
                             # We can match against all_researchers loaded previously.
                             found_person = next((r for r in all_researchers if getattr(r, "name", "").lower() == m_name.lower()), None)
                             
                             if found_person:
                                 m_person_id = getattr(found_person, "id")
                                 
                                 # Map Role
                                 # Lattes roles: "Coordenador", "Integrante", etc.
                                 role_key = "Researcher" # Default
                                 if "coordenador" in m_role_str.lower():
                                     role_key = "Coordinator"
                                 elif "estudante" in m_role_str.lower() or "bolsista" in m_role_str.lower():
                                     role_key = "Student"
                                 
                                 m_role = entity_manager.ensure_roles().get(role_key)
                                 m_role_id = getattr(m_role, "id")
                                 
                                 # Add Member
                                 try:
                                     team_ctrl.add_member(
                                         team_id=target_team_id,
                                         person_id=m_person_id,
                                         role_id=m_role_id,
                                         start_date=start_date,
                                         end_date=end_date
                                     )
                                 except Exception as mem_err:
                                     # Ignore duplicate membership constraint errors
                                     pass
                except Exception as team_err:
                    logger.warning(f"Failed to process team for initiative {init_id}: {team_err}")

            except Exception as e:
                logger.error(f"Error creating project {p['name']}: {e}")

        # Ingest Academic Education
        if education_list:
            edu_ctrl = AcademicEducationController()
            
            for edu_data in education_list:
                try:
                    # 1. Organization (Institution) - MANDATORY
                    inst_name = edu_data.get("institution") or "Unknown Institution"
                    org_id = entity_manager.ensure_organization(name=inst_name)
                    if not org_id:
                        logger.warning(f"Skipping Education: Could not resolve organization for {inst_name}")
                        continue

                    # 2. Education Type - MANDATORY
                    # "degree" from parser holds "Doutorado", "Mestrado" etc.
                    type_name = edu_data.get("degree") or "Unknown"
                    type_id = entity_manager.ensure_education_type(name=type_name)
                    if not type_id:
                         logger.warning(f"Skipping Education: Could not resolve type {type_name}")
                         continue

                    # 3. Advisor Lookup (Optional)
                    advisor_id = None
                    description = edu_data.get("description", "")
                    if description:
                        # Regex for advisor: "Orientador: Name Name"
                        # Be careful with "Coorientador"
                        import re
                        # Look for "Orientador: <name>." or end of string
                        adv_match = re.search(r"Orientador:\s*([^.;]+)", description, re.IGNORECASE)
                        if adv_match:
                            adv_name = adv_match.group(1).strip()
                            # Lookup researcher
                            # This is expensive validation, assuming cache for now?
                            # Re-using logic from top of file or finding new
                            adv_res = next((r for r in all_researchers if getattr(r, "name", "").lower() == adv_name.lower()), None)
                            if adv_res:
                                advisor_id = getattr(adv_res, "id")
                                logger.info(f"Found Advisor: {adv_name} -> ID {advisor_id}")

                    # 4. Create Entity
                    # Mapping: title <- course_name
                    # Nullable mapping
                    start_val = edu_data.get("start_year")
                    if start_val is None: start_val = 0 # Schema says NOT NULL for start_year
                    
                    education = AcademicEducation(
                        researcher_id=person_id,
                        education_type_id=type_id,
                        title=edu_data.get("course_name") or "Untitled",
                        institution_id=org_id,
                        start_year=start_val,
                        end_year=edu_data.get("end_year"),
                        thesis_title=edu_data.get("thesis_title"),
                        advisor_id=advisor_id
                        # co_advisor_id and knowledge_areas pending parsing logic
                    )
                    edu_ctrl.create(education)
                except Exception as e:
                    logger.warning(f"Failed to ingest education item for {lattes_id}: {e}")
                    import traceback
                    traceback.print_exc()

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
        from src.core.domain.academic_education import AcademicEducation
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
             logger.warning("Dropped academic tables for schema update.")
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

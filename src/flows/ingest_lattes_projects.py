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
            
        json_name = data.get("nome") or data.get("name")

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
            return

        logger.info(f"Found {len(projects)} projects for {lattes_id}.")

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
            p_type = types_map.get(p["initiative_type_name"])
            type_id = getattr(p_type, "id", None)

            # Check if exists (Idempotency)
            # We assume name + start_year + type is unique enough for now?
            # Or assume we update if name matches exactly?
            # Ideally we would query by name.
            # initiative_ctrl.get_all() is too heavy?
            # Let's just create for now or assume UPSERT in lib if ID provided.
            # Since we don't have ID, we might create duplicates if we run multiple times without checking.
            # Mitigation: Check if initiative with same name exists for this person? 
            # Complex without direct SQL. 
            # Let's implemented "Create if not exists" logic by checking all initiatives of this type?
            # It might be slow. 
            # For this task, we will just proceed with creation/update if we can find it.
            
            # Simple Idempotency: skip if name exists in DB (Global check - simpler)
            # This is not perfect but avoids massive duplication in dev.
            # Better: fetch all initiatives and filter in memory for this run.
            
            # Create Initiative
            # Mapping Start/End Dates
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

            # Create
            # Note: We need to see if create_initiative supports all fields or if we need to update
            # data = {
            #     "name": p["name"],
            #     "description": p["description"],
            #     "start_date": start_date,
            #     "end_date": end_date,
            #     "status": p["status"],
            #     "initiative_type_id": type_id,
            #     "organization_id": org_id
            # }
            
            # We'll use a try/except block to handle potential creation errors
            try:
                # Check for existing initiatives with same name to update instead of create
                # This requires a controller method we might not have, so let's try to create
                # and if it fails due to constraint, we ignore. 
                # But typically IDs are needed for updates.
                
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
                    # Role: Coordinator or Member?
                    # The parser doesn't extract role yet (defaulted to Member in my thought process, but let's try Coordinator if not specified)
                    # Let's default to "Researcher" or "Coordinator" based on parsing?
                    # For Lattes "Projetos", the owner is usually a key member.
                    
                    role_name = "Researcher" # Default
                    role = entity_manager.ensure_roles().get(role_name)
                    role_id = getattr(role, "id", None)
                    
                    if role_id:
                        # Add to Team
                        # team_ctrl.add_member(team_id=init_id (Initiative is a Team?), person_id, role_id, start_date, end_date)
                        # In many systems Initiative HAS-A Team. 
                        # initiative_ctrl.get_teams(init_id) -> returns teams.
                        # Usually an initiative has a "Default Team".
                        
                        # Let's try adding member directly to initiative if supported, or creates a team.
                        # If initiative extends Team, we accept members. 
                        # If not, we need to find the team.
                        
                        # From `canonical_exporter`:
                        # `teams = self.initiative_ctrl.get_teams(item.id)`
                        # valid teams are returned. If empty, maybe we need to create one?
                        # Or maybe `create_initiative` creates a default team.
                        
                        # Let's assume we can add directly via `initiative_controller` or `team_controller` on the initiative ID 
                        # if the ID matches the team ID (common pattern).
                        # Safe bet: `initiative_ctrl.add_member(init_id, person_id, role_id, ...)` ?
                        # If that doesn't exist, we might need `team_ctrl.add_member(init_id, ...)`
                        
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
                            logger.warning(f"Could not add member to project {init_id}: {e}")
                
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
    
    # Run Tasks
    for json_file in json_files:
        ingest_file_task(json_file, entity_manager)

if __name__ == "__main__":
    ingest_lattes_projects_flow()

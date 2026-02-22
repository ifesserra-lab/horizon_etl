
import os
import glob
import json
from datetime import datetime
from typing import List, Dict, Any

from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import text

from src.adapters.sources.lattes_parser import LattesParser
from src.core.logic.entity_manager import EntityManager
from src.core.logic.initiative_linker import InitiativeLinker
from src.core.logic.person_matcher import PersonMatcher
from src.core.logic.team_synchronizer import TeamSynchronizer

from eo_lib import (
    InitiativeController,
    PersonController,
    TeamController,
    OrganizationController
)
from research_domain.controllers import (
    ResearcherController,
    ResearchGroupController
)
from eo_lib.infrastructure.database.postgres_client import PostgresClient

try:
    from research_domain.domain.entities.advisorship import Advisorship, AdvisorshipType
except ImportError:
    from eo_lib import Initiative as Advisorship
    AdvisorshipType = None

@task(name="Ingest Lattes Advisorships for File", cache_policy=NO_CACHE)
def ingest_advisorships_file_task(
    file_path: str, 
    entity_manager: EntityManager, 
    linker: InitiativeLinker, 
    person_matcher: PersonMatcher
):
    logger = get_run_logger()
    
    filename = os.path.basename(file_path)
    lattes_id = filename.replace(".json", "").split("_")[-1]

    if not lattes_id or not lattes_id.isdigit():
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON {file_path}: {e}")
        return

    # 1. Identify Supervisor (Owner of CV)
    researcher_ctrl = ResearcherController()
    all_researchers = researcher_ctrl.get_all()
    
    # Match by ID
    supervisor = next((r for r in all_researchers if str(getattr(r, "brand_id", "") or "") == lattes_id), None)
    
    if not supervisor:
        # Fallback Name Match
        json_name = data.get("nome") or data.get("name") or data.get("informacoes_pessoais", {}).get("nome_completo")
        if json_name:
             supervisor = next((r for r in all_researchers if getattr(r, "name", "").lower() == json_name.lower()), None)
    
    if not supervisor:
        logger.debug(f"Skipping Advisorships for {lattes_id}: Supervisor not found in DB.")
        return

    json_name = getattr(supervisor, "name", "Unknown")
    
    # 2. Parse Advisorships
    parser = LattesParser()
    advisorships = parser.parse_advisorships(data)
    
    if not advisorships:
        return

    logger.info(f"Processing {len(advisorships)} advisorships for {json_name}...")
    
    # 3. Process Each Advisorship
    initiative_ctrl = InitiativeController()
    
    db_client = PostgresClient()
    session = db_client.get_session()

    for item in advisorships:
        try:
            title = item["title"]
            student_name = item["student_name"]
            year = item["year"]
            status = item["status"] # 'Concluded' or 'In Progress'
            nature_raw = item["nature"]
            canonical_type = item["type"] # 'Master's Thesis', etc.
            
            # Ensure "Advisorship" Type or specific subtype exists
            type_obj = entity_manager.ensure_initiative_type(canonical_type)
            type_id = getattr(type_obj, "id")

            # Map Canonical Type string to Enum
            mapped_type = None
            if AdvisorshipType:
                # Mapping Dictionary
                type_mapping = {
                    "Master's Thesis": AdvisorshipType.MASTER_THESIS,
                    "PhD Thesis": AdvisorshipType.PHD_THESIS,
                    "Scientific Initiation": AdvisorshipType.SCIENTIFIC_INITIATION,
                    "Junior Scientific Initiation": AdvisorshipType.JUNIOR_SCIENTIFIC_INITIATION,
                    "Undergraduate Thesis": AdvisorshipType.UNDERGRADUATE_THESIS,
                    "Post-Doctorate": AdvisorshipType.POST_DOCTORATE,
                    "Post-Doc Supervision": AdvisorshipType.POST_DOCTORATE,
                    "Specialization": None, # Generic Advisorship
                    "Advisorship": None # Generic Advisorship
                }
                mapped_type = type_mapping.get(canonical_type)

            # Check Idempotency by Name only first (to handle Type updates)
            # Use LEFT JOIN to find if it exists as initiative but maybe not advisorship
            chk_sql = text("""
                SELECT i.id, adv.id, adv.type, i.initiative_type_id 
                FROM initiatives i
                LEFT JOIN advisorships adv ON adv.id = i.id
                WHERE LOWER(i.name) = LOWER(:title)
                LIMIT 1
            """)
            
            existing = session.execute(chk_sql, {"title": title}).fetchone()
            existing_id = existing[0] if existing else None
            existing_adv_id = existing[1] if existing else None
            existing_adv_type = existing[2] if existing else None
            existing_init_type = existing[3] if existing else None
            
            # Start/End Dates
            start_date = None
            if year:
                start_date = datetime(year, 1, 1)

            # Resolve Student Person
            student_person = person_matcher.match_or_create(student_name)
            
            if existing_id:
                logger.debug(f"Initiative exists: {title} (ID={existing_id})")
                
                # Check if it is missing from Advisorships table (orphaned/generic initiative)
                # If existing_adv_id is None, it means the row definitely doesn't exist in advisorships
                if existing_adv_id is None:
                     # It exists as Initiative but not Advisorship. Promote it.
                     try:
                        logger.info(f"Promoting Initiative {existing_id} to Advisorship")
                        
                        mapped_val = mapped_type.value if mapped_type else None
                        
                        # Insert into advisorships
                        # Note: we need supervisor_id and student_id. 
                        # We have supervisor_id from context, student_id from above validation
                        session.execute(
                            text("""
                                INSERT INTO advisorships (id, supervisor_id, student_id, type)
                                VALUES (:id, :sup_id, :stu_id, :type)
                            """),
                            {
                                "id": existing_id, 
                                "sup_id": getattr(supervisor, "id"), 
                                "stu_id": student_person.id, 
                                "type": mapped_val
                            }
                        )
                        
                        # Update Initiative Type to Advisorship (or specific subtype if we had IDs)
                        # We use canonical_type ID we resolved earlier (type_id)
                        session.execute(
                            text("UPDATE initiatives SET initiative_type_id = :tid WHERE id = :id"),
                            {"tid": type_id, "id": existing_id}
                        )
                        session.commit()
                     except Exception as e:
                        logger.error(f"Failed to promote initiative {title}: {e}")

                # Update Type if different or missing (and it IS an advisorship row)
                target_val = mapped_type.value if mapped_type else None
                
                if mapped_type and (existing_adv_type != target_val):
                    try:
                       # Update Advisorship Type
                       session.execute(
                           text("UPDATE advisorships SET type = :type WHERE id = :id"),
                           {"type": target_val, "id": existing_id}
                       )
                       # Update Initiative Type ID matches the new specific type
                       session.execute(
                           text("UPDATE initiatives SET initiative_type_id = :tid WHERE id = :id"),
                           {"tid": type_id, "id": existing_id}
                       )
                       session.commit()
                       logger.info(f"Updated Advisorship Type for {title} to {target_val}")
                    except Exception as e:
                        logger.error(f"Failed to update type: {e}")
                
                # ALWAYS Enforce Linkage (Supervisor/Student) for existing records
                # This fixes "Unlinked" or "Orphaned" advisorships that exist but have NULL supervisor_id
                try:
                    # student_person is resolved above
                    # supervisor is resolved at start of task
                    session.execute(
                        text("UPDATE advisorships SET supervisor_id = :sup, student_id = :stu WHERE id = :id"),
                        {
                            "sup": getattr(supervisor, "id"), 
                            "stu": getattr(student_person, "id"),
                            "id": existing_id
                        }
                    )
                    session.commit()
                except Exception as e:
                     logger.error(f"Failed to enforce linkage for {title}: {e}")

                # Fetch the (potentially updated/promoted) entity for linking
                new_adv = initiative_ctrl.get_by_id(existing_id)
            else:
                # Create Advisorship (Initiative)
                # Pass supervisor_id and student_id specifically for Advisorship table
                new_adv = Advisorship(
                    name=title,
                    description=f"Inst: {item.get('institution', 'N/A')} - Natureza: {nature_raw}",
                    start_date=start_date,
                    status=status,
                    initiative_type_id=type_id,
                    organization_id=entity_manager.ensure_organization(), # Default IFES
                    supervisor_id=getattr(supervisor, "id"),
                    student_id=getattr(student_person, "id"),
                    type=mapped_type
                )
                
                initiative_ctrl.create(new_adv)
                adv_id = getattr(new_adv, "id")
                logger.info(f"Created Advisorship: {title} (ID: {adv_id})")
                
                # Force Update FKs (ORM seems to fail or Controller converts to base Initiative)
                try:
                    upd_sql = text("UPDATE advisorships SET supervisor_id = :sup, student_id = :stu WHERE id = :id")
                    session.execute(upd_sql, {
                        "sup": getattr(supervisor, "id"), 
                        "stu": getattr(student_person, "id"), 
                        "id": adv_id
                    })
                    session.commit()
                except Exception as e:
                    logger.error(f"Failed to update Advisorship FKs: {e}")

            # Link Team Members
            project_data = {
                "coordinator_name": getattr(supervisor, "name"), 
                "student_names": [student_name],
                "start_date": start_date
            }
            
            linker.add_members_to_initiative_team(new_adv, project_data)
            
        except Exception as e:
            logger.error(f"Failed to ingest advisorship '{item.get('title')}': {e}")
            if session:
                session.rollback()

    if session:
        try:
            session.commit()
        except Exception as e:
            logger.error(f"Failed to commit advisorships for {json_name}: {e}")

@flow(name="Ingest Lattes Advisorships Flow")
def ingest_lattes_advisorships_flow():
    base_dir = "data/lattes_json"
    if not os.path.isabs(base_dir):
        base_dir = os.path.join(os.getcwd(), base_dir)
        
    json_files = glob.glob(os.path.join(base_dir, "*.json"))
    
    if not json_files:
        logger = get_run_logger()
        logger.warning(f"No JSON files found in {base_dir}")
        return

    # Setup Components
    init_ctrl = InitiativeController()
    person_ctrl = PersonController()
    rg_ctrl = ResearchGroupController()
    team_ctrl = TeamController()
    
    # Build Roles Cache (Using TeamController's session to ensure attached objects)
    roles_cache = {}
    try:
        from eo_lib.domain.entities.role import Role
        
        # Use TeamController's session
        session = team_ctrl._service._repository._session
        
        all_roles = session.query(Role).all()
        
        for r in all_roles:
            roles_cache[r.name] = r
            
    except Exception as e:
        logger = get_run_logger()
        logger.warning(f"Failed to load roles for cache: {e}")
    
    entity_manager = EntityManager(init_ctrl, person_ctrl)
    person_matcher = PersonMatcher(person_ctrl)
    
    # Initialize TeamSynchronizer with CORRECT args
    team_sync = TeamSynchronizer(team_ctrl, roles_cache)
    
    linker = InitiativeLinker(
        initiative_controller=init_ctrl,
        rg_controller=rg_ctrl,
        team_controller=team_ctrl,
        person_matcher=person_matcher,
        team_synchronizer=team_sync,
        entity_manager=entity_manager
    )

    for json_file in json_files:
        ingest_advisorships_file_task(json_file, entity_manager, linker, person_matcher)

if __name__ == "__main__":
    ingest_lattes_advisorships_flow()

import re
import unicodedata
from typing import Any, Dict, Optional

from eo_lib import (
    Initiative,
    InitiativeController,
    Person,
    PersonController,
    TeamController,
)
from eo_lib.domain import Role
from eo_lib.infrastructure.database.postgres_client import PostgresClient
from loguru import logger
from research_domain import ResearchGroupController, CampusController, KnowledgeAreaController

from src.core.logic.person_matcher import PersonMatcher
from src.core.logic.team_synchronizer import TeamSynchronizer


class ProjectLoader:
    """
    Orchestrates the loading of project initiatives from external sources (e.g., Excel).

    This class manages the end-to-end ingestion flow, including ensuring necessary
    domain entities (Organization, Roles, InitiativeTypes) exist, and delegating
    the heavy lifting of person matching and team synchronization to specialized services.

    Attributes:
        mapping_strategy (BaseMappingStrategy): The strategy for parsing source columns.
        db_client (PostgresClient): Client for database interactions.
        controller (InitiativeController): Controller for managing projects.
        person_controller (PersonController): Controller for managing persons.
        team_controller (TeamController): Controller for managing teams.
        person_matcher (PersonMatcher): Service for person identification.
        team_synchronizer (TeamSynchronizer): Service for team and membership management.
    """

    ROLES = ["Coordinator", "Researcher", "Student"]

    def __init__(self, mapping_strategy):
        """
        Initializes the ProjectLoader with a specific mapping strategy.

        Args:
            mapping_strategy (BaseMappingStrategy): The strategy to use for data mapping.
        """
        self.mapping_strategy = mapping_strategy
        self.controller = InitiativeController()
        self.person_controller = PersonController()
        self.team_controller = TeamController()
        self.rg_controller = ResearchGroupController()
        self.campus_controller = CampusController()
        self.ka_controller = KnowledgeAreaController()

        # Service Classes
        self.person_matcher = PersonMatcher(self.person_controller)
        self._roles_cache: Dict[str, Role] = {}
        self._ensure_roles_exist()  # Populates _roles_cache

        self.team_synchronizer = TeamSynchronizer(
            self.team_controller, self._roles_cache
        )

        # Ensure "Research Project" type exists
        self.initiative_type = self._ensure_initiative_type_exists()

        # Ensure IFES Organization exists
        self.org_id = self._ensure_organization_exists()

    def _ensure_organization_exists(self) -> Optional[int]:
        """Ensure IFES organization exists."""
        from research_domain import UniversityController

        uni_ctrl = UniversityController()
        try:
            orgs = uni_ctrl.get_all()
            for o in orgs:
                name = o.name if hasattr(o, "name") else o.get("name")
                if "IFES" in name.upper():
                    return o.id if hasattr(o, "id") else o.get("id")

            # If not found, create one (Basic)
            logger.info("Creating IFES Organization...")
            ifes = uni_ctrl.create_university(
                name="Instituto Federal do Espírito Santo", short_name="IFES"
            )
            return ifes.id if hasattr(ifes, "id") else ifes.get("id")
        except Exception as e:
            logger.warning(f"Failed to ensure organization: {e}")
            return None

    def _ensure_roles_exist(self) -> None:
        """Create Coordinator, Researcher, Student roles if they don't exist and populate cache."""
        from research_domain import RoleController

        try:
            role_ctrl = RoleController()
            existing_roles = role_ctrl.get_all()

            # Map existing roles by name
            db_roles = {}
            for r in existing_roles:
                r_name = r.name if hasattr(r, "name") else r.get("name")
                if r_name:
                    db_roles[r_name] = r

            for role_name in self.ROLES:
                if role_name not in db_roles:
                    logger.info(f"Creating role: {role_name}")
                    new_role = role_ctrl.create_role(
                        name=role_name, description=f"Role: {role_name}"
                    )
                    self._roles_cache[role_name] = new_role
                else:
                    logger.debug(f"Role already exists: {role_name}")
                    self._roles_cache[role_name] = db_roles[role_name]
        except Exception as e:
            logger.warning(f"Error ensuring roles exist: {e}")
            # Fallback to direct DB access
            try:
                client = PostgresClient()
                session = client.get_session()
                for role_name in self.ROLES:
                    existing = session.query(Role).filter_by(name=role_name).first()
                    if not existing:
                        new_role = Role(
                            name=role_name, description=f"Role: {role_name}"
                        )
                        session.add(new_role)
                        session.commit()
                        logger.info(f"Created role: {role_name}")
                        self._roles_cache[role_name] = new_role
                    else:
                        self._roles_cache[role_name] = existing
            except Exception as e2:
                logger.error(f"Critical failure ensuring roles: {e2}")

    def _ensure_initiative_type_exists(self):
        """
        Ensures that the 'Research Project' initiative type exists in the database.

        Returns:
            Any: The InitiativeType object from the database.
        """
        type_name = "Research Project"
        initiative_type = None

        existing_types = self.controller.list_initiative_types()
        for t in existing_types:
            t_name = t.get("name") if isinstance(t, dict) else getattr(t, "name", "")
            if t_name == type_name:
                if isinstance(t, dict):

                    class Obj:
                        pass

                    initiative_type = Obj()
                    initiative_type.id = t.get("id")
                    initiative_type.name = t.get("name")
                else:
                    initiative_type = t
                break

        if not initiative_type:
            logger.info(f"Creating Initiative Type: {type_name}")
            try:
                new_type_result = self.controller.create_initiative_type(
                    name=type_name,
                    description="Projetos de Pesquisa importados do SigPesq",
                )

                if isinstance(new_type_result, dict):

                    class Obj:
                        pass

                    initiative_type = Obj()
                    initiative_type.id = new_type_result.get("id")
                    initiative_type.name = new_type_result.get("name")
                else:
                    initiative_type = new_type_result

            except Exception as e:
                logger.error(f"Failed to create initiative type: {e}")
                raise e

        return initiative_type

    def _create_initiative_team(self, initiative, project_data: Dict[str, Any]) -> None:
        """
        Creates a team for the given initiative and synchronizes its members based on data.

        This method identifies the team name (usually the initiative name), ensures its existence,
        and then identifies coordinators, researchers, and students to be members.
        It utilizes TeamSynchronizer for member tracking and synchronization.

        Args:
            initiative (Any): The Initiative entity.
            project_data (Dict[str, Any]): Dictionary containing project member names.
        """
        team_name = initiative.name[:200]
        team = self.team_synchronizer.ensure_team(
            team_name=team_name,
            description=f"Equipe do projeto: {initiative.name[:100]}",
        )

        if not team:
            return

        members_to_sync = []
        strict = True  # SigPesq requirement
        start_date = project_data.get("start_date")

        # 1. Map Names to Person objects using PersonMatcher
        # Coordinator
        coord_name = project_data.get("coordinator_name")
        if coord_name:
            p = self.person_matcher.match_or_create(coord_name, strict_match=strict)
            if p:
                members_to_sync.append((p, "Coordinator", start_date))

        # Researchers
        for name in project_data.get("researcher_names", []):
            p = self.person_matcher.match_or_create(name, strict_match=strict)
            if p:
                members_to_sync.append((p, "Researcher", start_date))

        # Students
        for name in project_data.get("student_names", []):
            p = self.person_matcher.match_or_create(name, strict_match=strict)
            if p:
                members_to_sync.append((p, "Student", start_date))

        # 2. Delegate synchronization to TeamSynchronizer
        self.team_synchronizer.synchronize_members(team.id, members_to_sync)

        # 3. Link team to initiative (remain in controller)
        try:
            self.controller.assign_team(initiative.id, team.id)
        except Exception as e:
            logger.warning(f"Failed to assign team to initiative: {e}")

    def process_file(self, file_path: str) -> None:
        """
        Reads the file, maps rows to Initiatives, and persists them.
        Uses UPSERT logic: updates existing initiatives, creates new ones.
        Also creates Teams with Persons for each initiative.
        """
        import pandas as pd

        logger.info(f"Processing Projects from: {file_path}")

        try:
            df = pd.read_excel(file_path)
            df = df.fillna("")
        except Exception as e:
            logger.error(f"Failed to read Excel file {file_path}: {e}")
            return

        # Fetch existing initiatives to implement UPSERT
        logger.info("Fetching existing initiatives for UPSERT logic...")
        existing_initiatives = self.controller.get_all()
        existing_by_name = {init.name: init for init in existing_initiatives}
        logger.info(f"Found {len(existing_by_name)} existing initiatives in database")

        # Pre-load persons cache
        self.person_matcher.preload_cache()
        initial_persons_count = len(self.person_matcher._persons_cache)

        created_count = 0
        updated_count = 0
        skipped_count = 0
        teams_created = 0

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            try:
                # 1. Map to Dict
                project_data = self.mapping_strategy.map_row(row_dict)

                # 2. Check strict fields and approval status
                parecer = row_dict.get("ParecerDiretoria", "Aprovado")
                if isinstance(parecer, str) and parecer.strip() and "aprovado" not in parecer.lower():
                    logger.info(f"Skipping project '{row_dict.get('Título', 'Unknown')}' due to ParecerDiretoria: {parecer}")
                    skipped_count += 1
                    continue

                if not project_data.get("title"):
                    logger.warning("Skipping row due to missing 'title'")
                    skipped_count += 1
                    continue

                title = project_data["title"]
                initiative = None

                # 3. UPSERT Logic: Check if initiative exists
                if title in existing_by_name:
                    # UPDATE existing initiative
                    initiative = existing_by_name[title]
                    logger.debug(f"Updating existing initiative: {title[:50]}...")

                    self.controller.update_initiative(
                        initiative_id=initiative.id,
                        name=title,
                        status=project_data.get("status", "Unknown"),
                        description=project_data.get("description"),
                        start_date=project_data.get("start_date"),
                        end_date=project_data.get("end_date"),
                        initiative_type_name=self.initiative_type.name,
                    )
                    # Force organization update
                    try:
                        initiative.organization_id = self.org_id
                        self.controller.update(initiative)
                    except Exception:
                        pass

                    updated_count += 1
                else:
                    # CREATE new initiative
                    logger.debug(f"Creating new initiative: {title[:50]}...")

                    initiative = Initiative(
                        name=title,
                        status=project_data.get("status", "Unknown"),
                        start_date=project_data.get("start_date"),
                        end_date=project_data.get("end_date"),
                        description=project_data.get("description"),
                        initiative_type_id=self.initiative_type.id,
                        organization_id=self.org_id,
                    )

                    if "metadata" in project_data:
                        initiative.metadata = project_data["metadata"]

                    self.controller.create(initiative)
                    created_count += 1

                if initiative:
                    self._create_initiative_team(initiative, project_data)
                    teams_created += 1
                    
                    # 5. Link to Research Group
                    rg_name = project_data.get("research_group_name")
                    campus_name = project_data.get("campus_name")
                    
                    if rg_name and isinstance(rg_name, str) and rg_name.strip():
                         self._link_research_group(initiative, rg_name, project_data, campus_name)
                         
                    # 6. Associate Keywords as Knowledge Areas (US-017)
                    self._associate_keyword_knowledge_areas(initiative, project_data, rg_name)

            except Exception as e:
                logger.warning(f"Skipping project row due to error: {e}")
                skipped_count += 1
                continue

        new_persons_count = (
            len(self.person_matcher._persons_cache) - initial_persons_count
        )

        logger.info(
            f"Project ingestion complete: "
            f"{created_count} created, {updated_count} updated, {skipped_count} skipped | "
            f"{teams_created} teams created, {new_persons_count} new persons"
        )
    
    def _resolve_campus(self, campus_name: Optional[str]) -> Optional[int]:
        """
        Resolves a campus name to an ID. If not found or name is empty, tries to find 'Reitoria' or returns None.
        """
        if not campus_name or not isinstance(campus_name, str):
            # Default to Reitoria or just pick the first one associated with IFES
            campus_name = "Reitoria"
            
        try:
            campuses = self.campus_controller.get_all()
            
            # 1. Exact/Normalized match
            def normalize(s):
                return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("utf-8").upper().strip()
                
            target_norm = normalize(campus_name)
            
            for c in campuses:
                c_name = c.name if hasattr(c, "name") else c.get("name")
                if c_name and normalize(c_name) == target_norm:
                    return c.id if hasattr(c, "id") else c.get("id")
                    
            # 2. If not found, create? Or return None?
            # Better to create if it looks like a valid name
            if len(campus_name) > 3:
                logger.info(f"Creating missing Campus: {campus_name}")
                new_campus = self.campus_controller.create_campus(
                     name=campus_name,
                     organization_id=self.org_id
                )
                return new_campus.id if hasattr(new_campus, "id") else new_campus.get("id")
                
        except Exception as e:
            logger.warning(f"Error resolving campus '{campus_name}': {e}")
            
        return None

    def _ensure_knowledge_area(self, name: str) -> Optional[int]:
        """Ensure Knowledge Area exists."""
        if not name:
            return None
        
        # Simple normalization
        try:
             norm_name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8").strip()
        except:
             return None
        
        try:
            # We assume get_all is fine for now
            all_kas = self.ka_controller.get_all()
            for ka in all_kas:
                k_name = ka.name if hasattr(ka, "name") else ka.get("name")
                if k_name:
                    try:
                        k_norm = unicodedata.normalize("NFD", k_name).encode("ascii", "ignore").decode("utf-8").strip().lower()
                        if k_norm == norm_name.lower():
                            return ka.id if hasattr(ka, "id") else ka.get("id")
                    except:
                        continue
            
            # Create
            logger.info(f"Creating Knowledge Area from keyword: {name}")
            new_ka = self.ka_controller.create_knowledge_area(name=name)
            return new_ka.id if hasattr(new_ka, "id") else new_ka.get("id")
            
        except Exception as e:
            logger.warning(f"Failed to ensure Knowledge Area '{name}': {e}")
            return None

    def _associate_keyword_knowledge_areas(self, initiative: Any, project_data: Dict[str, Any], rg_name: str) -> None:
        """
        Parses keywords, ensures KAs exist, and links them to:
        1. The Initiative directly (US-017 Refined)
        2. The Research Group (if found)
        3. The Researchers (members of the project).
        """
        metadata = project_data.get("metadata", {})
        keywords_str = metadata.get("keywords")
        
        if not keywords_str:
            return
            
        # Parse keywords (semicolon or comma separated)
        if ";" in str(keywords_str):
            keywords = [k.strip() for k in str(keywords_str).split(";") if k.strip()]
        else:
             keywords = [k.strip() for k in str(keywords_str).split(",") if k.strip()]
             
        if not keywords:
            return

        ka_ids = []
        for kw in keywords:
            kid = self._ensure_knowledge_area(kw)
            if kid:
                ka_ids.append(kid)
        
        if not ka_ids:
            return

        # 1. Associate with Initiative
        if initiative:
             iid = getattr(initiative, "id", None)
             if iid:
                 self._link_kas_to_initiative(iid, ka_ids)

        # 2. Associate with Research Group
        if rg_name:
             self._link_kas_to_group(rg_name, ka_ids)

        # 2. Associate with Researchers
        member_names = []
        if project_data.get("coordinator_name"):
            member_names.append(project_data.get("coordinator_name"))
        member_names.extend(project_data.get("researcher_names", []))
        
        for name in member_names:
            person = self.person_matcher.match_or_create(name, strict_match=True)
            if person:
                self._link_kas_to_researcher(person.id, ka_ids)

    def _link_kas_to_initiative(self, initiative_id: Any, ka_ids: list) -> None:
        try:
            from sqlalchemy import text
            session = self.rg_controller._service._repository._session
            
            for aid in ka_ids:
                try:
                    check = text("SELECT 1 FROM initiative_knowledge_areas WHERE initiative_id = :iid AND area_id = :aid")
                    exists = session.execute(check, {"iid": initiative_id, "aid": aid}).scalar()
                    
                    if not exists:
                        ins = text("INSERT INTO initiative_knowledge_areas (initiative_id, area_id) VALUES (:iid, :aid)")
                        session.execute(ins, {"iid": initiative_id, "aid": aid})
                        logger.debug(f"Linked KA {aid} to Initiative {initiative_id}")
                except Exception as e:
                    logger.warning(f"Failed handling KA {aid} for Initiative {initiative_id}: {e}")
            
            try:
                session.commit()
            except:
                session.rollback()
                
        except Exception as e:
            logger.warning(f"Failed to link KAs to Initiative {initiative_id}: {e}")

    def _link_kas_to_group(self, rg_name: str, ka_ids: list) -> None:
        try:
             # Find group
            all_groups = self.rg_controller.get_all()
            target_group = None
            
            def normalize(s):
                return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("utf-8").upper().strip()

            target_norm = normalize(rg_name)
            
            for group in all_groups:
                g_name = group.name if hasattr(group, "name") else group.get("name")
                if g_name and normalize(g_name) == target_norm:
                    target_group = group
                    break
            
            if not target_group:
                return

            gid = target_group.id if hasattr(target_group, "id") else target_group.get("id")
            
            # Use direct SQL for association to 'group_knowledge_areas'
            from sqlalchemy import text
            session = self.rg_controller._service._repository._session
            
            for aid in ka_ids:
                try:
                    check = text("SELECT 1 FROM group_knowledge_areas WHERE group_id = :gid AND area_id = :aid")
                    exists = session.execute(check, {"gid": gid, "aid": aid}).scalar()
                    
                    if not exists:
                        ins = text("INSERT INTO group_knowledge_areas (group_id, area_id) VALUES (:gid, :aid)")
                        session.execute(ins, {"gid": gid, "aid": aid})
                        logger.debug(f"Linked KA {aid} to Group {gid}")
                except Exception as e:
                    logger.warning(f"Failed handling KA {aid} for Group {gid}: {e}")
            
            # Commit after processing all KAs for this group
            try:
                session.commit()
            except:
                session.rollback()

        except Exception as e:
            logger.warning(f"Failed to link KAs to Group {rg_name}: {e}")

    def _link_kas_to_researcher(self, person_id: Any, ka_ids: list) -> None:
        try:
            # We need to treat Person as Researcher to access 'researcher_knowledge_areas'
            from sqlalchemy import text
            
            # Use same session
            session = self.rg_controller._service._repository._session
            
            # 1. Ensure in researchers table
            chk_res = text("SELECT 1 FROM researchers WHERE id = :rid")
            is_res = session.execute(chk_res, {"rid": person_id}).scalar()
            
            if not is_res:
                try:
                     ins_res = text("INSERT INTO researchers (id) VALUES (:rid)")
                     session.execute(ins_res, {"rid": person_id})
                     session.commit()
                except Exception:
                     # If conflicting concurrent update, maybe it exists now
                     session.rollback()
            
            # 2. Link KAs
            for aid in ka_ids:
                 try:
                    check = text("SELECT 1 FROM researcher_knowledge_areas WHERE researcher_id = :rid AND area_id = :aid")
                    exists = session.execute(check, {"rid": person_id, "aid": aid}).scalar()
                    
                    if not exists:
                        ins = text("INSERT INTO researcher_knowledge_areas (researcher_id, area_id) VALUES (:rid, :aid)")
                        session.execute(ins, {"rid": person_id, "aid": aid})
                        logger.debug(f"Linked KA {aid} to Researcher {person_id}")
                 except Exception as e:
                    logger.warning(f"Failed handling KA {aid} for Researcher {person_id}: {e}")
            
            try:
                session.commit()
            except:
                session.rollback()
            
        except Exception as e:
            logger.warning(f"Failed to link KAs to Researcher {person_id}: {e}")

    def _link_research_group(self, initiative, rg_name: str, project_data: Dict[str, Any], campus_name: Optional[str] = None) -> None:
        """
        Links an initiative to a Research Group by name. Creates it if missing using campus_name.
        """
        try:
            # Simple linear search for now as get_by_name might not exist or be efficient
            # In a production scenario with many groups, we should cache this mapping.
            # But since we have few groups (ingested in US-007), fetching all might be fine.
            
            # TODO: Improve efficiency with a cache if needed
            all_groups = self.rg_controller.get_all()
            target_group = None
            
            # Normalize for comparison
            def normalize(s):
                return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("utf-8").upper().strip()

            target_norm = normalize(rg_name)
            
            for group in all_groups:
                g_name = group.name if hasattr(group, "name") else group.get("name")
                if g_name and normalize(g_name) == target_norm:
                    target_group = group
                    break
            
            if not target_group:
                logger.info(f"Research Group '{rg_name}' not found. Creating new group...")
                
                campus_id = self._resolve_campus(campus_name)
                
                if not campus_id:
                     logger.warning(f"Could not resolve campus for RG '{rg_name}'. Cannot create.")
                     return

                try:
                    # Create new Research Group
                    target_group = self.rg_controller.create_research_group(
                        name=rg_name,
                        description=f"Grupo de Pesquisa importado do SigPesq: {rg_name}",
                        organization_id=self.org_id,
                        campus_id=campus_id
                    )
                    logger.info(f"Created new Research Group: {rg_name} (Campus ID: {campus_id})")
                except Exception as e_create:
                    logger.error(f"Failed to create Research Group '{rg_name}': {e_create}")
                    return
                
                # RF-15: Auto-populate members for newly created groups
                if target_group:
                    self._populate_group_members(target_group, initiative, project_data)

            if target_group:
                # WORKAROUND: eo_lib.Team is not configured for polymorphism with ResearchGroup.
                # So we cannot add a ResearchGroup object to Initiative.teams (which expects Team).
                # However, ResearchGroup inherits from Team (Joined Inheritance likely), so they share keys.
                # We fetch the underlying Team object by ID and link that instead.
                
                try:
                     # Access ID safely whether it's an object or dict (if controller returns dict)
                     tg_id = target_group.id if hasattr(target_group, "id") else target_group.get("id")
                     
                     team_proxy = self.team_controller.get_by_id(tg_id)
                     if team_proxy:
                         
                         # Check if already linked
                         is_linked = False
                         # We can check existing initiatives on the team proxy
                         # Note: relationship might be named 'initiatives' on Team too.
                         # Let's check the inspect output: Team has backref 'initiatives' from Initiative.teams
                         
                         if hasattr(team_proxy, "initiatives"):
                             for init in team_proxy.initiatives:
                                 if init.id == initiative.id:
                                     is_linked = True
                                     break
                         
                         if not is_linked:
                             if hasattr(team_proxy, "initiatives"):
                                 team_proxy.initiatives.append(initiative)
                                 self.team_controller.update(team_proxy)
                                 logger.info(f"Linked Initiative '{initiative.name[:30]}...' to Research Group '{rg_name}' (via Team {tg_id})")
                             else:
                                  # Fallback: try adding team to initiative
                                  initiative.teams.append(team_proxy)
                                  self.controller.update(initiative)
                                  logger.info(f"Linked Initiative '{initiative.name[:30]}...' to Research Group '{rg_name}' (via Initiative.teams)")

                     else:
                         logger.warning(f"Could not find base Team for Research Group {tg_id}")
                         
                except Exception as e_link:
                     logger.warning(f"Failed to link Team proxy for RG: {e_link}")
                
        except Exception as e:
            logger.warning(f"Failed to link Research Group '{rg_name}': {e}")

    def _populate_group_members(self, group: Any, initiative: Any, project_data: Dict[str, Any]) -> None:
        """
        Populates a newly created Research Group with members from the project.
        - Coordinator/Researchers -> 'Researcher'
        - Students -> 'Student'
        """
        try:
            # We need the Team ID corresponding to the Group
            gid = group.id if hasattr(group, "id") else group.get("id")
            
            # The 'team' might be the group itself if they share IDs (Joined Inheritance)
            # or we need to find the team. TeamController.get_by_id(gid) works for us.
            
            members_to_sync = []
            strict = True
            
            # Use project's start date as member start date in the group
            start_date = project_data.get("start_date")
            
            # 1. Coordinator & Researchers -> Role: Researcher
            names_researcher = []
            if project_data.get("coordinator_name"):
                names_researcher.append(project_data.get("coordinator_name"))
            names_researcher.extend(project_data.get("researcher_names", []))
            
            for name in names_researcher:
                p = self.person_matcher.match_or_create(name, strict_match=strict)
                if p:
                    # Role: Researcher
                    members_to_sync.append((p, "Researcher", start_date))
            
            # 2. Students -> Role: Student
            for name in project_data.get("student_names", []):
                p = self.person_matcher.match_or_create(name, strict_match=strict)
                if p:
                    # Role: Student
                    members_to_sync.append((p, "Student", start_date))
            
            if members_to_sync:
                logger.info(f"Populating new Group {gid} with {len(members_to_sync)} members from project...")
                # We can use TeamSynchronizer to add these members to the group's team
                self.team_synchronizer.synchronize_members(gid, members_to_sync)
                logger.info(f"Successfully populated Group {gid} members.")
            else:
                logger.info(f"No members found to populate Group {gid}.")
                
        except Exception as e:
            logger.warning(f"Failed to populate members for Group {group.name if hasattr(group, 'name') else 'Unknown'}: {e}")

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

                # 2. Check strict fields
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

                # 4. Create Team with Persons
                if initiative:
                    self._create_initiative_team(initiative, project_data)
                    teams_created += 1

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

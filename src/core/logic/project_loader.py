import unicodedata
import re
from thefuzz import process, fuzz
from typing import List, Any, Dict, Optional
from loguru import logger
from eo_lib import (
    InitiativeController,
    Initiative,
    InitiativeType,
    PersonController,
    TeamController,
    Person,
)
from eo_lib.domain import Role
from eo_lib.infrastructure.database.postgres_client import PostgresClient


class ProjectLoader:
    """
    Loads Project (Initiative) entities into the database.

    This class is responsible for:
    1. Parsing the Excel file using a Strategy.
    2. Instantiating Initiative entities.
    3. Creating Team with Persons (Coordinator, Researchers, Students).
    4. Persisting them using Controllers.
    """

    ROLES = ["Coordinator", "Researcher", "Student"]

    def __init__(self, mapping_strategy):
        self.mapping_strategy = mapping_strategy
        self.controller = InitiativeController()
        self.person_controller = PersonController()
        self.team_controller = TeamController()

        # Cache for persons by name (for idempotency)
        self._persons_cache: Dict[str, Person] = {}

        # Ensure roles exist
        self._ensure_roles_exist()

        # Ensure "Research Project" type exists
        self.initiative_type = self._ensure_initiative_type_exists()

    def _ensure_roles_exist(self) -> None:
        """Create Coordinator, Researcher, Student roles if they don't exist."""
        client = PostgresClient()
        session = client.get_session()

        for role_name in self.ROLES:
            existing = session.query(Role).filter_by(name=role_name).first()
            if not existing:
                new_role = Role(name=role_name, description=f"Role: {role_name}")
                session.add(new_role)
                logger.info(f"Created role: {role_name}")

        session.commit()

    def _ensure_initiative_type_exists(self):
        """Ensure 'Research Project' initiative type exists."""
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
                    name=type_name, description="Projetos de Pesquisa importados do SigPesq"
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

    def _normalize_name(self, name: str) -> str:
        """
        Normalizes person name for consistent identification:
        - Removes accents
        - Removes special characters (keeps only letters and spaces)
        - Converts to uppercase
        - Removes extra spaces
        """
        if not name:
            return ""

        # 1. Normalize Unicode (NFD) and remove accents
        name_str = "".join(
            c
            for c in unicodedata.normalize("NFD", name)
            if unicodedata.category(c) != "Mn"
        )

        # 2. Replace special characters with spaces and Uppercase
        name_str = re.sub(r"[^A-Z\s]", " ", name_str.upper())

        # 3. Trim and remove double spaces
        return " ".join(name_str.split())

    def _get_or_create_person(self, name: str) -> Optional[Person]:
        """Find person by name using Normalization and Fuzzy Matching or create if not exists."""
        if not name or not name.strip():
            return None

        name = name.strip()
        normalized_input = self._normalize_name(name)

        # 1. Exact Match in Cache (Normalized)
        # Check if normalized input matches any normalized name in cache
        for cached_name, person in self._persons_cache.items():
            if self._normalize_name(cached_name) == normalized_input:
                # Add this variation to cache for faster exact lookup next time
                self._persons_cache[name] = person
                return person

        # 2. Fuzzy Matching in Cache
        # If no exact match, try fuzzy matching against cached names
        names_in_cache = list(self._persons_cache.keys())
        if names_in_cache:
            # Create a mapping of normalized names to original names for the cache
            normalized_to_original = {
                self._normalize_name(n): n for n in names_in_cache
            }
            normalized_list = list(normalized_to_original.keys())

            # extractOne returns (match, score)
            best_norm_match, score = process.extractOne(
                normalized_input, normalized_list, scorer=fuzz.token_sort_ratio
            )

            # Threshold of 90% for considering it the same person
            if score >= 90:
                original_name = normalized_to_original[best_norm_match]
                logger.info(
                    f"Fuzzy match found: '{name}' matches '{original_name}' (score: {score})"
                )
                person = self._persons_cache[original_name]
                # Add this variation to cache
                self._persons_cache[name] = person
                return person

        # 3. Create new person (if no match found)
        try:
            person = self.person_controller.create_person(name=name)
            self._persons_cache[name] = person
            logger.debug(f"Created person: {name}")
            return person
        except Exception as e:
            logger.warning(f"Failed to create person '{name}': {e}")
            return None

    def _get_role_id(self, role_name: str) -> Optional[int]:
        """Get role ID by name."""
        client = PostgresClient()
        session = client.get_session()
        role = session.query(Role).filter_by(name=role_name).first()
        return role.id if role else None

    def _create_initiative_team(
        self, initiative, project_data: Dict[str, Any]
    ) -> None:
        """Create team and assign members for an initiative."""
        # 1. Check if initiative already has a team linked
        try:
            # We can check via the controller if the initiative has a team
            # Based on the Initiative schema, it might have a team_id or similar
            # For now, we list teams and check name, which is what we have.
            pass
        except Exception:
            pass

        # Create team with same name as project
        team_name = initiative.name[:200]  # Limit name length

        try:
            # Check if team already exists
            existing_teams = self.team_controller.list_teams()
            team = None
            for t in existing_teams:
                t_name = t.name if hasattr(t, "name") else (t.get("name") if isinstance(t, dict) else "")
                if t_name == team_name:
                    team = t
                    logger.debug(f"Team already exists for project: {team_name[:50]}...")
                    break
            
            if not team:
                team = self.team_controller.create_team(
                    name=team_name, description=f"Equipe do projeto: {initiative.name[:100]}"
                )
                logger.info(f"Created team: {team_name[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to manage team for '{team_name[:50]}': {e}")
            return

        persons_added = 0

        # Add coordinator
        coord_name = project_data.get("coordinator_name")
        if coord_name:
            person = self._get_or_create_person(coord_name)
            if person:
                try:
                    self.team_controller.add_member(
                        team_id=team.id,
                        person_id=person.id,
                        role="Coordinator",
                        start_date=project_data.get("start_date"),
                    )
                    persons_added += 1
                except Exception as e:
                    logger.warning(f"Failed to add coordinator: {e}")

        # Add researchers
        for name in project_data.get("researcher_names", []):
            person = self._get_or_create_person(name)
            if person:
                try:
                    self.team_controller.add_member(
                        team_id=team.id,
                        person_id=person.id,
                        role="Researcher",
                        start_date=project_data.get("start_date"),
                    )
                    persons_added += 1
                except Exception as e:
                    logger.warning(f"Failed to add researcher '{name}': {e}")

        # Add students
        for name in project_data.get("student_names", []):
            person = self._get_or_create_person(name)
            if person:
                try:
                    self.team_controller.add_member(
                        team_id=team.id,
                        person_id=person.id,
                        role="Student",
                        start_date=project_data.get("start_date"),
                    )
                    persons_added += 1
                except Exception as e:
                    logger.warning(f"Failed to add student '{name}': {e}")

        # Link team to initiative
        try:
            self.controller.assign_team(initiative.id, team.id)
            logger.debug(f"Assigned team to initiative (added {persons_added} members)")
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
        logger.info("Loading persons cache...")
        all_persons = self.person_controller.get_all()
        self._persons_cache = {p.name: p for p in all_persons}
        logger.info(f"Loaded {len(self._persons_cache)} persons into cache")

        created_count = 0
        updated_count = 0
        skipped_count = 0
        teams_created = 0
        persons_created_count = len(self._persons_cache)

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            try:
                # 1. Map to Dict
                project_data = self.mapping_strategy.map_row(row_dict)

                # 2. Check strict fields
                if not project_data.get("title"):
                    logger.warning(f"Skipping row due to missing 'title'")
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

        new_persons_count = len(self._persons_cache) - persons_created_count

        logger.info(
            f"Project ingestion complete: "
            f"{created_count} created, {updated_count} updated, {skipped_count} skipped | "
            f"{teams_created} teams created, {new_persons_count} new persons"
        )

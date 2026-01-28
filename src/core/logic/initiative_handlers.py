from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from eo_lib import (
    Initiative,
    InitiativeController,
)
from research_domain import (
    AdvisorshipController,
    FellowshipController,
)
from research_domain.domain.entities import Advisorship, Fellowship
from loguru import logger


class BaseInitiativeHandler(ABC):
    """Base class for handling specific initiative types during ingestion."""

    def __init__(self, initiative_controller: InitiativeController):
        self.initiative_controller = initiative_controller

    @abstractmethod
    def create_or_update(self, project_data: Dict[str, Any], existing_initiative: Optional[Any], initiative_type_name: str, initiative_type_id: int, organization_id: Optional[int], parent_id: Optional[int] = None) -> Any:
        """Creates or updates the initiative entity."""
        pass


class StandardProjectHandler(BaseInitiativeHandler):
    """Handler for standard research projects."""

    def create_or_update(self, project_data: Dict[str, Any], existing_initiative: Optional[Any], initiative_type_name: str, initiative_type_id: int, organization_id: Optional[int], parent_id: Optional[int] = None) -> Any:
        title = project_data["title"]
        
        if existing_initiative:
            logger.debug(f"Updating existing initiative: {title[:50]}...")
            self.initiative_controller.update_initiative(
                initiative_id=existing_initiative.id,
                name=title,
                status=project_data.get("status", "Unknown"),
                description=project_data.get("description"),
                start_date=project_data.get("start_date"),
                end_date=project_data.get("end_date"),
                initiative_type_name=initiative_type_name,
            )
            # Force organization and parent update if possible
            try:
                existing_initiative.organization_id = organization_id
                if parent_id is not None:
                    existing_initiative.parent_id = parent_id
                self.initiative_controller.update(existing_initiative)
            except Exception:
                pass
            return existing_initiative
        else:
            logger.debug(f"Creating new initiative: {title[:50]}...")
            initiative = Initiative(
                name=title,
                status=project_data.get("status", "Unknown"),
                start_date=project_data.get("start_date"),
                end_date=project_data.get("end_date"),
                description=project_data.get("description"),
                initiative_type_id=initiative_type_id,
                organization_id=organization_id,
                parent_id=parent_id,
            )
            if "metadata" in project_data:
                initiative.metadata = project_data["metadata"]
            
            self.initiative_controller.create(initiative)
            return initiative


class AdvisorshipHandler(BaseInitiativeHandler):
    """Handler for Advisorships and Fellowships."""

    def __init__(self, initiative_controller: InitiativeController, person_matcher):
        super().__init__(initiative_controller)
        self.adv_controller = AdvisorshipController()
        self.fel_controller = FellowshipController()
        self.person_matcher = person_matcher
        self._fellowships_cache: Dict[str, Fellowship] = {}
        self._preload_fellowships()

    def _preload_fellowships(self):
        """Preload fellowships into cache."""
        try:
            all_fels = self.fel_controller.get_all()
            for f in all_fels:
                name = f.name if hasattr(f, "name") else f.get("name")
                if name:
                    self._fellowships_cache[name] = f
        except Exception as e:
            logger.warning(f"Failed to preload fellowships: {e}")

    def create_or_update(self, project_data: Dict[str, Any], existing_initiative: Optional[Any], initiative_type_name: str, initiative_type_id: int, organization_id: Optional[int], parent_id: Optional[int] = None) -> Any:
        title = project_data["title"]
        
        if existing_initiative:
            # Advisorship update logic (using standard initiative update as base)
            logger.debug(f"Updating existing advisorship: {title[:50]}...")
            self.initiative_controller.update_initiative(
                initiative_id=existing_initiative.id,
                name=title,
                status=project_data.get("status", "Unknown"),
                description=project_data.get("description"),
                start_date=project_data.get("start_date"),
                end_date=project_data.get("end_date"),
                initiative_type_name=initiative_type_name,
            )
            # Force organization and parent update if possible
            try:
                existing_initiative.organization_id = organization_id
                if parent_id is not None:
                    existing_initiative.parent_id = parent_id
                self.initiative_controller.update(existing_initiative)
            except Exception:
                pass
            
            # Update specialized fields
            # If it's a base Initiative, we MUST fetch it as Advisorship to access specialized fields
            target_adv = existing_initiative
            if not isinstance(existing_initiative, Advisorship):
                try:
                    # Fetch specialized record by ID
                    actual_adv = self.adv_controller.get_by_id(existing_initiative.id)
                    if actual_adv:
                        target_adv = actual_adv
                    else:
                        logger.warning(f"Initiative {existing_initiative.id} is not an Advisorship in the DB.")
                        return existing_initiative
                except Exception as e:
                    logger.warning(f"Failed to fetch Advisorship detail for {existing_initiative.id}: {e}")
                    return existing_initiative

            try:
                self._handle_advisorship_details(target_adv, project_data)
                self.adv_controller.update(target_adv)
            except Exception as e:
                logger.warning(f"Could not update advisorship-specific details for {title}: {e}")
                
            return target_adv
        else:
            logger.debug(f"Creating new advisorship: {title[:50]}...")
            initiative = Advisorship(
                name=title,
                status=project_data.get("status", "Unknown"),
                start_date=project_data.get("start_date"),
                end_date=project_data.get("end_date"),
                description=project_data.get("description"),
                initiative_type_id=initiative_type_id,
                organization_id=organization_id,
                parent_id=parent_id,
            )
            if "metadata" in project_data:
                initiative.metadata = project_data["metadata"]

            self._handle_advisorship_details(initiative, project_data)
            self.adv_controller.create(initiative)
            return initiative

    def _handle_advisorship_details(self, initiative: Advisorship, project_data: Dict[str, Any]) -> None:
        """Handles Student, Supervisor, and Fellowships for an Advisorship."""
        strict = True  # SigPesq requirement

        # 1. Student
        student_name = project_data.get("student_names", [None])[0]
        student_email = project_data.get("student_emails", [None])[0]
        if student_name or student_email:
            p = self.person_matcher.match_or_create(student_name, email=student_email, strict_match=strict)
            if p:
                initiative.student_id = p.id
                initiative.student = p

        # 2. Supervisor
        supervisor_name = project_data.get("coordinator_name")
        supervisor_email = project_data.get("coordinator_email")
        if supervisor_name or supervisor_email:
            p = self.person_matcher.match_or_create(supervisor_name, email=supervisor_email, strict_match=strict)
            if p:
                initiative.supervisor_id = p.id
                initiative.supervisor = p

        # 3. Fellowship
        fellowship_data = project_data.get("fellowship_data")
        if fellowship_data:
            f_name = fellowship_data["name"]
            fellowship = self._fellowships_cache.get(f_name)
            
            if not fellowship:
                fellowship = Fellowship(
                    name=f_name,
                    value=fellowship_data.get("value", 0.0),
                    description=fellowship_data.get("description"),
                )
                self.fel_controller.create(fellowship)
                self._fellowships_cache[f_name] = fellowship
            
            initiative.fellowship = fellowship
            initiative.fellowship_id = fellowship.id

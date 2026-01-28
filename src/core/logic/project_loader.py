from typing import Any, Dict, Optional
import pandas as pd
from loguru import logger

from eo_lib import (
    Initiative,
    InitiativeController,
    PersonController,
    TeamController,
)
from research_domain import (
    AdvisorshipController,
    CampusController,
    FellowshipController,
    KnowledgeAreaController,
    ResearchGroupController,
)
from research_domain.domain.entities import Advisorship

from src.core.logic.person_matcher import PersonMatcher
from src.core.logic.team_synchronizer import TeamSynchronizer
from src.core.logic.entity_manager import EntityManager
from src.core.logic.initiative_handlers import StandardProjectHandler, AdvisorshipHandler
from src.core.logic.initiative_linker import InitiativeLinker


class ProjectLoader:
    """
    Orchestrates the loading of project initiatives from external sources.
    Delegates specific tasks to specialized handlers, managers, and linkers.
    """

    def __init__(self, mapping_strategy):
        self.mapping_strategy = mapping_strategy
        
        # Controllers
        self.controller = InitiativeController()
        self.person_controller = PersonController()
        self.team_controller = TeamController()
        self.rg_controller = ResearchGroupController()
        self.adv_controller = AdvisorshipController()
        
        # Service/Logic Classes
        self.entity_manager = EntityManager(self.controller, self.person_controller)
        self.person_matcher = PersonMatcher(self.person_controller)
        
        # Initialize Roles and Cache
        roles_cache = self.entity_manager.ensure_roles()
        
        self.team_synchronizer = TeamSynchronizer(self.team_controller, roles_cache)
        
        self.linker = InitiativeLinker(
            initiative_controller=self.controller,
            rg_controller=self.rg_controller,
            team_controller=self.team_controller,
            person_matcher=self.person_matcher,
            team_synchronizer=self.team_synchronizer,
            entity_manager=self.entity_manager
        )
        
        # Handlers registry
        self.handlers = {
            Initiative: StandardProjectHandler(self.controller),
            Advisorship: AdvisorshipHandler(self.controller, self.person_matcher)
        }
        
        # Ensure base environment
        self.initiative_type = self.entity_manager.ensure_initiative_type("Research Project")
        self.org_id = self.entity_manager.ensure_organization()

    def process_file(self, file_path: str) -> None:
        """
        Reads the file, maps rows, and orchestrates the UPSERT logic across handlers and linkers.
        """
        logger.info(f"Processing Projects from: {file_path}")

        try:
            df = pd.read_excel(file_path)
            df = df.fillna("")
        except Exception as e:
            logger.error(f"Failed to read Excel file {file_path}: {e}")
            return

        logger.info("Fetching existing initiatives for UPSERT...")
        existing_initiatives = self.controller.get_all()
        existing_by_name = {init.name: init for init in existing_initiatives}

        self.person_matcher.preload_cache()
        initial_persons_count = len(self.person_matcher._persons_cache)

        stats = {"created": 0, "updated": 0, "skipped": 0, "teams": 0}

        for _, row in df.iterrows():
            try:
                self._process_row(row.to_dict(), existing_by_name, stats)
            except Exception as e:
                logger.warning(f"Skipping row due to error: {e}")
                stats["skipped"] += 1
                self._rollback_session()

        new_persons_count = len(self.person_matcher._persons_cache) - initial_persons_count
        logger.info(
            f"Ingestion complete: {stats['created']} created, {stats['updated']} updated, "
            f"{stats['skipped']} skipped | {stats['teams']} teams, {new_persons_count} new persons"
        )

    def _process_row(self, row_dict: Dict[str, Any], existing_by_name: Dict[str, Any], stats: Dict[str, int]) -> None:
        # 1. Map to Dict
        project_data = self.mapping_strategy.map_row(row_dict)

        # 2. Validation
        if not self._is_approved(row_dict) or not project_data.get("title"):
            stats["skipped"] += 1
            return

        title = project_data["title"]
        model_class = project_data.get("model_class", Initiative)
        handler = self.handlers.get(model_class, self.handlers[Initiative])

        # 2.5 Parent Initiative Handling
        parent_id = None
        parent_initiative = None
        parent_title = project_data.get("parent_title")
        if parent_title:
            parent_initiative = existing_by_name.get(parent_title)
            if not parent_initiative:
                # Create parent via Standard Handler
                logger.info(f"Creating parent Research Project: {parent_title}")
                
                # Ensure we have the "Research Project" type for the parent
                res_proj_type = self.entity_manager.ensure_initiative_type("Research Project")
                
                parent_initiative = self.handlers[Initiative].create_or_update(
                    project_data={"title": parent_title},
                    existing_initiative=None,
                    initiative_type_name="Research Project",
                    initiative_type_id=res_proj_type.id,
                    organization_id=self.org_id
                )
                existing_by_name[parent_title] = parent_initiative
            
            parent_id = parent_initiative.id

        # 3. UPSERT Initiative
        existing = existing_by_name.get(title)
        initiative = handler.create_or_update(
            project_data=project_data,
            existing_initiative=existing,
            initiative_type_name=self.initiative_type.name,
            initiative_type_id=self.initiative_type.id,
            organization_id=self.org_id,
            parent_id=parent_id
        )

        if not existing:
            stats["created"] += 1
        else:
            stats["updated"] += 1

        # 3.5 Link Advisorship members to Parent Project
        if parent_id and parent_initiative:
            self.linker.add_members_to_initiative_team(parent_initiative, project_data)

        # 4. Linkages
        if initiative:
            # Team synchronization
            self.linker.create_initiative_team(initiative, project_data)
            stats["teams"] += 1

            # Research Group linkage
            rg_name = project_data.get("research_group_name")
            if rg_name and isinstance(rg_name, str) and rg_name.strip():
                self.linker.link_research_group(
                    initiative, rg_name, project_data, 
                    project_data.get("campus_name"), self.org_id
                )

            # Knowledge Areas / Keywords
            self.linker.associate_keyword_knowledge_areas(initiative, project_data, rg_name)

    def _is_approved(self, row_dict: Dict[str, Any]) -> bool:
        parecer = row_dict.get("ParecerDiretoria", "Aprovado")
        if isinstance(parecer, str) and parecer.strip() and "aprovado" not in parecer.lower():
            logger.info(f"Skipping project '{row_dict.get('Título', 'Unknown')}' - Not Approved")
            return False
        return True

    def _rollback_session(self):
        try:
            self.controller._service._repository._session.rollback()
        except Exception:
            pass

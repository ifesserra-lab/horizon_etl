import os
from typing import Any, List, Optional

from eo_lib import InitiativeController, OrganizationController
from loguru import logger
from research_domain import (
    CampusController,
    KnowledgeAreaController,
    ResearcherController,
)

from src.core.ports.export_sink import IExportSink


class CanonicalDataExporter:
    def __init__(self, sink: IExportSink):
        self.sink = sink
        self.org_ctrl = OrganizationController()
        self.campus_ctrl = CampusController()
        self.ka_ctrl = KnowledgeAreaController()
        self.researcher_ctrl = ResearcherController()
        self.initiative_ctrl = InitiativeController()

    def _export_entities(self, data: List[Any], output_path: str, entity_name: str):
        """
        Helper to serialize and export a list of entities.
        """
        logger.info(f"Exporting {len(data)} {entity_name}...")
        try:
            export_data = []
            for item in data:
                if isinstance(item, dict):
                    export_data.append(item)
                elif hasattr(item, "to_dict"):
                    export_data.append(item.to_dict())
                else:
                    # Fallback for entities without to_dict (should not happen with SerializableMixin)
                    export_data.append(
                        {
                            "id": getattr(item, "id", None),
                            "name": getattr(item, "name", "Unknown"),
                        }
                    )

            self.sink.export(export_data, output_path)
            logger.info(f"Successfully exported {entity_name} to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export {entity_name}: {e}")
            raise e

    def export_organizations(self, output_path: str):
        data = self.org_ctrl.get_all()
        self._export_entities(data, output_path, "Organizations")

    def export_campuses(self, output_path: str, campus_filter: Optional[str] = None):
        data = self.campus_ctrl.get_all()
        if campus_filter:
            data = [c for c in data if c.name.lower() == campus_filter.lower()]
        self._export_entities(data, output_path, "Campuses")

    def export_knowledge_areas(self, output_path: str):
        data = self.ka_ctrl.get_all()
        self._export_entities(data, output_path, "Knowledge Areas")

    def export_researchers(self, output_path: str):
        data = self.researcher_ctrl.get_all()
        self._export_entities(data, output_path, "Researchers")

    def export_initiatives(self, output_path: str):
        from eo_lib import TeamController

        team_ctrl = TeamController()
        initiatives = self.initiative_ctrl.get_all()
        types = {t.id: t for t in self.initiative_ctrl.list_initiative_types()}
        orgs = {o.id: o for o in self.org_ctrl.get_all()}

        serialized_data = []
        for item in initiatives:
            # Enriched Initiative Type
            init_type = types.get(item.initiative_type_id)
            type_data = (
                {
                    "id": init_type.id,
                    "name": init_type.name,
                    "description": getattr(init_type, "description", None),
                }
                if init_type
                else None
            )

            # Enriched Organization
            org = orgs.get(item.organization_id)
            org_data = (
                {
                    "id": org.id,
                    "name": org.name,
                    "short_name": getattr(org, "short_name", None),
                }
                if org
                else None
            )

            # Enriched Team
            team_list = []
            try:
                teams = self.initiative_ctrl.get_teams(item.id)
                for t_dict in teams:
                    t_id = t_dict.get("id")
                    if t_id:
                        members = team_ctrl.get_members(t_id)
                        for m in members:
                            team_list.append(
                                {
                                    "person_id": m.person_id,
                                    "person_name": (
                                        m.person.name if m.person else "Unknown"
                                    ),
                                    "role": m.role.name if m.role else "Member",
                                    "start_date": (
                                        m.start_date.isoformat()
                                        if m.start_date
                                        else None
                                    ),
                                    "end_date": (
                                        m.end_date.isoformat() if m.end_date else None
                                    ),
                                }
                            )
            except Exception as e:
                logger.warning(f"Could not fetch teams for initiative {item.id}: {e}")

            serialized_data.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "status": item.status,
                    "description": item.description,
                    "start_date": (
                        item.start_date.isoformat() if item.start_date else None
                    ),
                    "end_date": item.end_date.isoformat() if item.end_date else None,
                    "initiative_type_id": item.initiative_type_id,
                    "initiative_type": type_data,
                    "organization_id": item.organization_id,
                    "organization": org_data,
                    "parent_id": item.parent_id,
                    "team": team_list,
                }
            )

        logger.info(f"Exporting {len(serialized_data)} enriched Initiatives...")
        self.sink.export(serialized_data, output_path)
        logger.info(f"Successfully exported enriched Initiatives to {output_path}")

    def export_initiative_types(self, output_path: str):
        data = self.initiative_ctrl.list_initiative_types()
        self._export_entities(data, output_path, "Initiative Types")

    def export_all(self, output_dir: str):
        """
        Exports all canonical data to the specified directory.
        Generates: organizations, campuses, knowledge_areas, researchers, initiatives, initiative_types
        """
        logger.info(f"Starting Canonical Data Export to {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

        self.export_organizations(
            os.path.join(output_dir, "organizations_canonical.json")
        )
        self.export_campuses(os.path.join(output_dir, "campuses_canonical.json"))
        self.export_knowledge_areas(
            os.path.join(output_dir, "knowledge_areas_canonical.json")
        )
        self.export_researchers(os.path.join(output_dir, "researchers_canonical.json"))
        self.export_initiatives(os.path.join(output_dir, "initiatives_canonical.json"))
        self.export_initiative_types(
            os.path.join(output_dir, "initiative_types_canonical.json")
        )

        logger.info("Canonical Data Export completed.")

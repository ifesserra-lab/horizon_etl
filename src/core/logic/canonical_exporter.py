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
    """
    Exports domain entities from the database to canonical JSON files.

    This class orchestrates the extraction of various entities (Organizations, Campuses,
    Knowledge Areas, Researchers, Initiatives) using their respective controllers
    and serializes them into a standardized format for external consumption.

    Attributes:
        sink (IExportSink): The destination for the exported data (e.g., File, S3).
        org_ctrl (OrganizationController): Controller for organizations.
        campus_ctrl (CampusController): Controller for campuses.
        ka_ctrl (KnowledgeAreaController): Controller for knowledge areas.
        researcher_ctrl (ResearcherController): Controller for researchers.
        initiative_ctrl (InitiativeController): Controller for initiatives.
    """

    def __init__(self, sink: IExportSink):
        """
        Initializes the CanonicalDataExporter.

        Args:
            sink (IExportSink): The strategy for exporting the data.
        """
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
        """
        Exports all organizations to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
        data = self.org_ctrl.get_all()
        self._export_entities(data, output_path, "Organizations")

    def export_campuses(self, output_path: str, campus_filter: Optional[str] = None):
        """
        Exports campuses to a JSON file, optionally filtered by name.

        Args:
            output_path (str): The destination file path.
            campus_filter (Optional[str]): name of campus to filter.
        """
        data = self.campus_ctrl.get_all()
        if campus_filter:
            data = [c for c in data if c.name.lower() == campus_filter.lower()]
        self._export_entities(data, output_path, "Campuses")

    def export_knowledge_areas(self, output_path: str):
        """
        Exports all knowledge areas to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
        data = self.ka_ctrl.get_all()
        self._export_entities(data, output_path, "Knowledge Areas")

    def export_researchers(self, output_path: str):
        """
        Exports all researchers to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
        data = self.researcher_ctrl.get_all()
        self._export_entities(data, output_path, "Researchers")

    def export_initiatives(self, output_path: str):
        """
        Exports enriched initiatives (with types, organizations, and team members) to a JSON file.

        This method aggregates data from multiple controllers to provide a complete
        view of each initiative, including its team structure with roles.

        Args:
            output_path (str): The destination file path.
        """
        from eo_lib import TeamController

        team_ctrl = TeamController()
        initiatives = self.initiative_ctrl.get_all()

        # Normalize types and orgs to handle both dicts and objects
        raw_types = self.initiative_ctrl.list_initiative_types()
        types = {}
        for t in raw_types:
            t_id = t.get("id") if isinstance(t, dict) else getattr(t, "id", None)
            if t_id:
                types[t_id] = t

        raw_orgs = self.org_ctrl.get_all()
        orgs = {}
        for o in raw_orgs:
            o_id = o.get("id") if isinstance(o, dict) else getattr(o, "id", None)
            if o_id:
                orgs[o_id] = o

        serialized_data = []
        for item in initiatives:
            # Enriched Initiative Type
            init_type = types.get(item.initiative_type_id)
            if init_type:
                type_data = {
                    "id": (
                        init_type.get("id")
                        if isinstance(init_type, dict)
                        else getattr(init_type, "id", None)
                    ),
                    "name": (
                        init_type.get("name")
                        if isinstance(init_type, dict)
                        else getattr(init_type, "name", None)
                    ),
                    "description": (
                        init_type.get("description")
                        if isinstance(init_type, dict)
                        else getattr(init_type, "description", None)
                    ),
                }
            else:
                type_data = None

            # Enriched Organization
            org = orgs.get(item.organization_id)
            if org:
                org_data = {
                    "id": (
                        org.get("id")
                        if isinstance(org, dict)
                        else getattr(org, "id", None)
                    ),
                    "name": (
                        org.get("name")
                        if isinstance(org, dict)
                        else getattr(org, "name", None)
                    ),
                    "short_name": (
                        org.get("short_name")
                        if isinstance(org, dict)
                        else getattr(org, "short_name", None)
                    ),
                }
            else:
                org_data = None

            # Enriched Team
            team_list = []
            try:
                teams = self.initiative_ctrl.get_teams(item.id)
                for t_dict in teams:
                    t_id = t_dict.get("id")
                    if t_id:
                        members = team_ctrl.get_members(t_id)

                        # Aggregate roles by person
                        person_map = {}  # person_id -> member_data
                        for m in members:
                            p_id = m.person_id
                            if p_id not in person_map:
                                person_map[p_id] = {
                                    "person_id": p_id,
                                    "person_name": (
                                        m.person.name if m.person else "Unknown"
                                    ),
                                    "roles": [],  # Collect role names here
                                    "start_date": (
                                        m.start_date.isoformat()
                                        if m.start_date
                                        else None
                                    ),
                                    "end_date": (
                                        m.end_date.isoformat() if m.end_date else None
                                    ),
                                }

                            role_name = m.role.name if m.role else "Member"
                            if role_name not in person_map[p_id]["roles"]:
                                person_map[p_id]["roles"].append(role_name)

                        # Add aggregated members to team_list
                        for p_data in person_map.values():
                            # For backward compatibility or if single role is preferred string,
                            # we can join roles, but let's use a list as requested/implied.
                            # The user said "a person has one or more roles, but it appears only once".
                            team_list.append(p_data)
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
        """
        Exports all initiative types to a JSON file.

        Args:
            output_path (str): The destination file path.
        """
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

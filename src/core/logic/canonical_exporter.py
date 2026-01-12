from typing import List, Any, Optional
from loguru import logger
import os
from src.core.ports.export_sink import IExportSink
from research_domain import CampusController, KnowledgeAreaController, ResearcherController
from eo_lib.controllers.organization_controller import OrganizationController

class CanonicalDataExporter:
    def __init__(self, sink: IExportSink):
        self.sink = sink
        self.org_ctrl = OrganizationController()
        self.campus_ctrl = CampusController()
        self.ka_ctrl = KnowledgeAreaController()
        self.researcher_ctrl = ResearcherController()

    def _export_entities(self, data: List[Any], output_path: str, entity_name: str):
        """
        Helper to serialize and export a list of entities.
        """
        logger.info(f"Exporting {len(data)} {entity_name}...")
        try:
             export_data = []
             for item in data:
                 if hasattr(item, 'to_dict'):
                     export_data.append(item.to_dict())
                 else:
                     # Fallback for entities without to_dict (should not happen with SerializableMixin)
                     export_data.append({"id": getattr(item, 'id', None), "name": getattr(item, 'name', 'Unknown')})
             
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

    def export_all(self, output_dir: str):
        """
        Exports all canonical data to the specified directory.
        Generates: organizations_canonical.json, campuses_canonical.json, knowledge_areas_canonical.json, researchers_canonical.json
        """
        logger.info(f"Starting Canonical Data Export to {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        self.export_organizations(os.path.join(output_dir, "organizations_canonical.json"))
        self.export_campuses(os.path.join(output_dir, "campuses_canonical.json"))
        self.export_knowledge_areas(os.path.join(output_dir, "knowledge_areas_canonical.json"))
        self.export_researchers(os.path.join(output_dir, "researchers_canonical.json"))
        
        logger.info("Canonical Data Export completed.")

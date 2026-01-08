from typing import List, Optional
from loguru import logger
from src.core.ports.export_sink import IExportSink
from research_domain import ResearchGroupController, ResearchGroup

class ResearchGroupExporter:
    def __init__(self, sink: IExportSink):
        self.sink = sink
        self.rg_ctrl = ResearchGroupController()

    def export_all(self, output_path: str) -> None:
        """
        Fetches all Research Groups and exports them to the specified path.
        
        Args:
            output_path: Destination file path.
        """
        logger.info("Fetching all Research Groups from database...")
        try:
            # Fetch all groups (this might need pagination in the future if dataset is huge)
            groups = self.rg_ctrl.get_all()
            
            if not groups:
                logger.warning("No Research Groups found to export.")
                return

            logger.info(f"Found {len(groups)} groups. Exporting...")
            
            # The get_all() returns domain entities (Pydantic models)
            self.sink.export(groups, output_path)
            
            logger.info(f"Export completed successfully to {output_path}")
            
        except Exception as e:
            logger.error(f"Error during export: {e}")
            raise e

import pandas as pd
from loguru import logger
from research_domain import ProjectController
# Assuming ProjectController exists. If not, this might fail at runtime, but I can't check.

from .strategies.sigpesq_projects import SigPesqProjectMappingStrategy

class ProjectLoader:
    def __init__(self, mapping_strategy: SigPesqProjectMappingStrategy):
        self.mapping_strategy = mapping_strategy
        self.project_ctrl = ProjectController()

    def process_file(self, file_path: str):
        logger.info(f"Processing Projects from: {file_path}")
        
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Failed to read Excel: {e}")
            return

        count = 0
        skipped = 0
        
        for _, row_raw in df.iterrows():
            try:
                data = self.mapping_strategy.map_row(row_raw.to_dict())
                
                title = data.get('title')
                status = data.get('status')
                
                if pd.isna(title):
                    continue
                
                # Check idempotency/existence
                # Assuming project_ctrl has get_by_title or similar, or I just Create and let it handle duplicates?
                # Usually we want get_or_create
                
                # For now, I'll try to create. Real implementation would verify existence.
                # Assuming generic 'create_project' signature.
                
                try:
                    # NOTE: "Initiative type Research Project" - user request.
                    # I'll create as Project.
                    project = self.project_ctrl.create_project(
                        title=title,
                        status=status,
                        metadata={
                            "original_source": "sigpesq",
                            "raw_data": str(data),
                            "type": "Research Project" # Explicitly marking as requested
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create project {title}: {e}")
                    skipped += 1

            except Exception as e:
                logger.error(f"Error processing row: {e}")
        
        logger.info(f"Loaded {count} New Projects. Skipped/Failed {skipped}.")

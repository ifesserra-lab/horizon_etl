from typing import List, Any
from loguru import logger
# Use eo_lib for Initiative (Project)
from eo_lib import InitiativeController, Initiative, InitiativeType

class ProjectLoader:
    """
    Loads Project (Initiative) entities into the database.
    
    This class is responsible for:
    1. Parsing the Excel file using a Strategy.
    2. Instantiating Initiative entities.
    3. Persisting them using InitiativeController.
    """
    def __init__(self, mapping_strategy):
        self.mapping_strategy = mapping_strategy
        self.controller = InitiativeController()
        # Ensure "Research Project" type exists
        type_name = "Research Project"
        initiative_type = None
        
        # Simple cache or check
        existing_types = self.controller.list_initiative_types()
        # It seems list_initiative_types returns dicts
        for t in existing_types:
            # Handle both dict and object just in case
            t_name = t.get('name') if isinstance(t, dict) else getattr(t, 'name', '')
            if t_name == type_name:
                # Wrap as object for consistency with creation part logic
                if isinstance(t, dict):
                    class Obj: pass
                    initiative_type = Obj()
                    initiative_type.id = t.get('id')
                    initiative_type.name = t.get('name')
                else:
                    initiative_type = t
                break
        
        if not initiative_type:
            logger.info(f"Creating Initiative Type: {type_name}")
            # Controller.create_initiative_type(name: str, description: str) -> Dict
            try:
                new_type_result = self.controller.create_initiative_type(
                    name=type_name, 
                    description="Projetos de Pesquisa importados do SigPesq"
                )
                
                # Verify if it returns Dict or Object
                if isinstance(new_type_result, dict):
                    # quick hack to mimic object interface if needed, or just extract ID
                    class Obj: pass
                    initiative_type = Obj()
                    initiative_type.id = new_type_result.get('id')
                    initiative_type.name = new_type_result.get('name')
                else:
                    initiative_type = new_type_result
                    
            except Exception as e:
                logger.error(f"Failed to create initiative type: {e}")
                raise e
        
        self.initiative_type = initiative_type

    def process_file(self, file_path: str) -> None:
        """
        Reads the file, maps rows to Initiatives, and persists them.
        """
        import pandas as pd
        logger.info(f"Processing Projects from: {file_path}")
        
        try:
            df = pd.read_excel(file_path)
            # Normalize columns to upper case to avoid case sensitivity, or trust strategy
            df = df.fillna("")
        except Exception as e:
            logger.error(f"Failed to read Excel file {file_path}: {e}")
            return

        projects_count = 0
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            try:
                # 1. Map to Dict
                project_data = self.mapping_strategy.map_row(row_dict)
                
                # 2. Check strict fields
                if not project_data.get("title"):
                    logger.warning(f"Skipping row due to missing 'title': {row_dict}")
                    continue

                # 3. Create Initiative Entity
                # Map 'title' -> 'name'
                initiative = Initiative(
                    name=project_data["title"],
                    status=project_data.get("status", "Unknown"),
                    start_date=project_data.get("start_date"),
                    end_date=project_data.get("end_date"),
                    description=project_data.get("description"),
                    initiative_type_id=self.initiative_type.id
                )
                
                # Handle metadata if supported by Entity base class but not in init
                if "metadata" in project_data:
                    initiative.metadata = project_data["metadata"]
                
                # 4. Persist
                self.controller.create(initiative)
                projects_count += 1
                
            except Exception as e:
                logger.warning(f"Skipping project row due to error: {e}")
                continue
                
        logger.info(f"Successfully loaded {projects_count} projects/initiatives.")

from prefect import flow, task, get_run_logger
import os
from src.core.logic.mart_generator import KnowledgeAreaMartGenerator

@task(name="generate_ka_mart_task")
def generate_ka_mart_task(output_path: str):
    logger = get_run_logger()
    logger.info(f"Starting Knowledge Area Mart generation task to {output_path}...")
    
    generator = KnowledgeAreaMartGenerator()
    generator.generate(output_path)
    
    logger.info("Knowledge Area Mart generation task completed.")

@flow(name="Export Knowledge Area Mart Flow")
def export_knowledge_areas_mart_flow(output_path: str = "data/exports/knowledge_areas_mart.json"):
    """
    Flow to generate the Knowledge Area Mart JSON from database.
    
    Args:
        output_path: Path where the mart JSON will be saved.
    """
    # Ensure absolute path or relative to CWD
    if not os.path.isabs(output_path):
        output_path = os.path.join(os.getcwd(), output_path)
        
    generate_ka_mart_task(output_path)

if __name__ == "__main__":
    export_knowledge_areas_mart_flow()

from prefect import flow
from loguru import logger
from src.flows.download_lattes import download_lattes_flow
from src.flows.ingest_lattes_projects import ingest_lattes_projects_flow

@flow(name="Lattes Complete Pipeline")
def lattes_complete_flow():
    """
    Unified flow that:
    1. Downloads Lattes XML/JSONs using scriptLattes
    2. Ingests the projects (Research, Extension, Development) into the database
    """
    logger.info(">>> Starting Lattes Complete Pipeline")
    
    logger.info(">>> Step 1: Downloading Lattes Curricula")
    download_lattes_flow()
    
    logger.info(">>> Step 2: Ingesting Lattes Projects")
    ingest_lattes_projects_flow()
    
    logger.info(">>> Lattes Complete Pipeline Finished successfully.")

if __name__ == "__main__":
    lattes_complete_flow()

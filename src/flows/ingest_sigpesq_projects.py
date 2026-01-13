from prefect import flow, task, get_run_logger
from dotenv import load_dotenv
from src.adapters.sources.sigpesq.adapter import SigPesqAdapter
from src.core.logic.project_loader import ProjectLoader
from src.core.logic.strategies.sigpesq_projects import SigPesqProjectMappingStrategy

load_dotenv()

@task
def persist_projects():
    """
    Finds the latest Projects Excel file and loads it into the database as Initiatives.
    """
    logger = get_run_logger()
    import glob
    import os
    
    # Find latest file
    files = glob.glob("data/raw/sigpesq/research_project/*.xlsx")
    if not files:
        logger.warning("No Project Excel files found in data/raw/sigpesq/research_project/.")
        return

    # Sort by mtime
    latest_file = max(files, key=os.path.getmtime)
    logger.info(f"Loading Projects from {latest_file}")
    
    loader = ProjectLoader(
        mapping_strategy=SigPesqProjectMappingStrategy()
    )
    loader.process_file(latest_file)

@flow(name="Ingest SigPesq Projects")
def ingest_projects_flow() -> None:
    """
    Flow specifically for ingesting Research Projects (Initiatives).
    """
    logger = get_run_logger()
    logger.info("Initializing SigPesq Projects Ingestion Flow")
    
    # Import strategies
    from agent_sigpesq.strategies import ProjectsDownloadStrategy
    
    adapter = SigPesqAdapter()
    
    # 1. Extract Only Projects
    logger.info("Extracting Projects...")
    adapter.extract(download_strategies=[ProjectsDownloadStrategy()])
    
    # 2. Persist Projects
    persist_projects()
    
    logger.info("Projects Ingestion finished successfully.")

if __name__ == "__main__":
    ingest_projects_flow()

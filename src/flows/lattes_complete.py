from prefect import flow, get_run_logger
from .download_lattes import download_lattes_flow
from .ingest_lattes_projects import ingest_lattes_projects_flow

@flow(name="Lattes Complete Pipeline")
def lattes_complete_flow():
    """
    Coordinates the full Lattes pipeline: 
    1. Downloads Lattes curricula (JSON) using scriptLattes.
    2. Ingests the downloaded JSON data into the database.
    """
    logger = get_run_logger()
    logger.info("Starting Lattes Complete Pipeline...")

    # 1. Download
    logger.info("Step 1/2: Downloading Lattes data...")
    download_lattes_flow()

    # 2. Ingest
    logger.info("Step 2/2: Ingesting Lattes data...")
    ingest_lattes_projects_flow()

    logger.info("Lattes Complete Pipeline finished successfully.")

if __name__ == "__main__":
    lattes_complete_flow()

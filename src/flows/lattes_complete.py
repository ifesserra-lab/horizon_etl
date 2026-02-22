from prefect import flow, get_run_logger
from .download_lattes import download_lattes_flow
from .ingest_lattes_projects import ingest_lattes_projects_flow
from .ingest_lattes_advisorships import ingest_lattes_advisorships_flow

@flow(name="Lattes Complete Pipeline")
def lattes_complete_flow():
    """
    Coordinates the full Lattes pipeline: 
    1. Downloads Lattes curricula (JSON) using scriptLattes.
    2. Ingests the downloaded JSON data into the database (Projects, Articles).
    3. Ingests Advisorships.
    """
    logger = get_run_logger()
    logger.info("Starting Lattes Complete Pipeline...")

    # 1. Download
    logger.info("Step 1/3: Downloading Lattes data...")
    download_lattes_flow()

    # 2. Ingest Projects/Articles
    logger.info("Step 2/3: Ingesting Lattes projects and articles...")
    ingest_lattes_projects_flow()

    # 3. Ingest Advisorships
    logger.info("Step 3/3: Ingesting Lattes advisorships...")
    ingest_lattes_advisorships_flow()

    logger.info("Lattes Complete Pipeline finished successfully.")

if __name__ == "__main__":
    lattes_complete_flow()

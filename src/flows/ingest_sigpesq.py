from prefect import flow, get_run_logger
from dotenv import load_dotenv

# Import the specific flows
from src.flows.ingest_sigpesq_groups import ingest_research_groups_flow
from src.flows.ingest_sigpesq_projects import ingest_projects_flow

load_dotenv()

@flow(name="Ingest SigPesq Full")
def ingest_sigpesq_flow() -> None:
    """
    Main Prefect Flow for ingesting ALL SigPesq data.
    Orchestrates the independent flows for Research Groups and Projects.
    """
    logger = get_run_logger()
    logger.info("Initializing SigPesq Full Ingestion Flow")

    # Run sub-flows
    ingest_research_groups_flow()
    ingest_projects_flow()

    logger.info("Flow finished successfully.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "projects":
            ingest_projects_flow()
        elif command == "groups":
            ingest_research_groups_flow()
        else:
            print(f"Unknown command: {command}. Running Full Flow.")
            ingest_sigpesq_flow()
    else:
        print("Running Full Flow (Default). usage: python ingest_sigpesq.py [projects|groups]")
        ingest_sigpesq_flow()

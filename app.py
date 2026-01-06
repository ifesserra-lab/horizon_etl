import sys

from dotenv import load_dotenv
from loguru import logger

from src.flows.ingest_sigpesq import ingest_sigpesq_flow

# Load environment variables
load_dotenv()


def main():
    """
    Main entry point for Horizon ETL.
    Currently runs the SigPesq Ingestion Flow.
    """
    logger.info("Starting Horizon ETL Application")

    try:
        # Future: Switch/Case or Argument Parser to run specific flows
        logger.info("Executing Flow: Ingest SigPesq")
        ingest_sigpesq_flow()

    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

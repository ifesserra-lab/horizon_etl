import sys
from dotenv import load_dotenv
from loguru import logger

from src.flows.ingest_sigpesq import ingest_sigpesq_flow
from src.flows.sync_cnpq_groups import sync_cnpq_groups_flow
from src.flows.export_canonical_data import export_canonical_data_flow
from src.flows.export_knowledge_areas_mart import export_knowledge_areas_mart_flow
from src.flows.unified_pipeline import full_ingestion_pipeline

# Load environment variables
load_dotenv()

import os
# Ensure connection to the local Prefect Server
os.environ.setdefault("PREFECT_API_URL", "http://127.0.0.1:4200/api")


def main():
    """
    Main entry point for Horizon ETL.
    Allows running specific flows based on arguments or sequentially.
    """
    logger.info("Starting Horizon ETL Application")

    # Simple argument handling
    flow_to_run = sys.argv[1] if len(sys.argv) > 1 else "all"

    try:
        if flow_to_run == "full_pipeline":
             campus_filter = sys.argv[2] if len(sys.argv) > 2 else None
             output_dir = sys.argv[3] if len(sys.argv) > 3 else "data/exports"
             logger.info(f"Executing FULL Pipeline (Campus: {campus_filter}, Output: {output_dir})")
             full_ingestion_pipeline(campus_name=campus_filter, output_dir=output_dir)

        elif flow_to_run in ["sigpesq", "all"]:
            logger.info("Executing Flow: Ingest SigPesq")
            ingest_sigpesq_flow()
        
        if flow_to_run in ["cnpq_sync", "all"]:
            campus_filter = sys.argv[2] if len(sys.argv) > 2 and flow_to_run == "cnpq_sync" else None
            logger.info(f"Executing Flow: Sync CNPq Groups (Campus Filter: {campus_filter})")
            sync_cnpq_groups_flow(campus_name=campus_filter)

        if flow_to_run in ["export_canonical", "all"]:
             # Optional output dir as 2nd arg if running specific flow
            output_dir = sys.argv[2] if len(sys.argv) > 2 and flow_to_run == "export_canonical" else "data/exports"
            logger.info(f"Executing Flow: Export Canonical Data (Output: {output_dir})")
            export_canonical_data_flow(output_dir=output_dir)

        if flow_to_run in ["ka_mart", "all"]:
            output_path = sys.argv[2] if len(sys.argv) > 2 and flow_to_run == "ka_mart" else "data/exports/knowledge_areas_mart.json"
            logger.info(f"Executing Flow: Export Knowledge Area Mart (Output: {output_path})")
            export_knowledge_areas_mart_flow(output_path=output_path)

    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

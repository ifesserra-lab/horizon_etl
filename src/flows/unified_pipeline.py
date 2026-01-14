import os
from typing import Optional

from prefect import flow, get_run_logger

from .export_canonical_data import export_canonical_data_flow
from .export_knowledge_areas_mart import export_knowledge_areas_mart_flow
from .ingest_sigpesq import ingest_sigpesq_flow
from .sync_cnpq_groups import sync_cnpq_groups_flow


@flow(name="Horizon Full Pipeline")
def full_ingestion_pipeline(
    campus_name: Optional[str] = None, output_dir: str = "data/exports"
):
    """
    Orchestrates the complete data pipeline:
    1. SigPesq Ingestion
    2. CNPq Synchronization
    3. Canonical Data Export
    4. Knowledge Area Mart Generation
    """
    logger = get_run_logger()
    logger.info("Starting Unified Ingestion Pipeline...")

    # 1. Ingest from SigPesq
    logger.info("Step 1/4: Ingesting SigPesq data...")
    ingest_sigpesq_flow()

    # 2. Sync with CNPq
    logger.info(f"Step 2/4: Syncing CNPq groups (Filter: {campus_name or 'None'})...")
    sync_cnpq_groups_flow(campus_name=campus_name)

    # 3. Export Canonical Data
    logger.info(f"Step 3/4: Exporting canonical data to {output_dir}...")
    export_canonical_data_flow(output_dir=output_dir)

    # 4. Generate Knowledge Area Mart
    mart_path = os.path.join(output_dir, "knowledge_areas_mart.json")
    logger.info(f"Step 4/4: Generating Knowledge Area Mart at {mart_path}...")
    export_knowledge_areas_mart_flow(output_path=mart_path, campus=campus_name)

    logger.info("Unified Ingestion Pipeline completed successfully.")


if __name__ == "__main__":
    full_ingestion_pipeline()

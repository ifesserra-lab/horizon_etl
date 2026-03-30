import os
from typing import Optional

from prefect import flow, get_run_logger

from src.core.logic.prefect_runtime import configure_local_prefect_runtime
from src.core.logic.etl_flow_reporter import (
    ETLFlowReporter,
    probe_cnpq_sync,
    probe_lattes_advisorships,
    probe_lattes_projects,
    probe_sigpesq_advisorships,
    probe_sigpesq_groups,
    probe_sigpesq_projects,
)
from .export_canonical_data import export_canonical_data_flow
from .export_initiatives_analytics_mart import export_initiatives_analytics_mart_flow
from .export_knowledge_areas_mart import export_knowledge_areas_mart_flow
from .ingest_lattes_advisorships import ingest_lattes_advisorships_flow
from .ingest_lattes_projects import ingest_lattes_projects_flow
from .ingest_sigpesq_advisorships import ingest_advisorships_flow
from .ingest_sigpesq_groups import ingest_research_groups_flow
from .ingest_sigpesq_projects import ingest_projects_flow
from .sync_cnpq_groups import sync_cnpq_groups_flow

configure_local_prefect_runtime()


@flow(name="Horizon Full Pipeline")
def full_ingestion_pipeline(
    campus_name: Optional[str] = None,
    output_dir: str = "data/exports",
    generate_etl_report: bool = True,
):
    """
    Orchestrates the complete data pipeline:
    1. SigPesq ingestion
    2. Lattes complete ingestion
    3. CNPq synchronization
    4. Canonical data export
    5. Knowledge Area mart generation
    6. Initiative analytics mart generation
    """
    logger = get_run_logger()
    logger.info("Starting Unified Ingestion Pipeline...")
    reporter = ETLFlowReporter(output_dir="data/reports", run_name="etl_flow_run") if generate_etl_report else None

    try:
        logger.info("Step 1/8: Ingesting SigPesq research groups...")
        if reporter:
            reporter.run_step(
                step_name="sigpesq_research_groups",
                runner=ingest_research_groups_flow,
                source_probe=probe_sigpesq_groups,
            )
        else:
            ingest_research_groups_flow()

        logger.info("Step 2/8: Ingesting SigPesq projects...")
        if reporter:
            reporter.run_step(
                step_name="sigpesq_projects",
                runner=ingest_projects_flow,
                source_probe=probe_sigpesq_projects,
            )
        else:
            ingest_projects_flow()

        logger.info("Step 3/8: Ingesting SigPesq advisorships...")
        if reporter:
            reporter.run_step(
                step_name="sigpesq_advisorships",
                runner=ingest_advisorships_flow,
                source_probe=probe_sigpesq_advisorships,
            )
        else:
            ingest_advisorships_flow()

        logger.info("Step 4/8: Ingesting Lattes projects/articles/education...")
        if reporter:
            reporter.run_step(
                step_name="lattes_projects",
                runner=ingest_lattes_projects_flow,
                source_probe=probe_lattes_projects,
            )
        else:
            ingest_lattes_projects_flow()

        logger.info("Step 5/8: Ingesting Lattes advisorships...")
        if reporter:
            reporter.run_step(
                step_name="lattes_advisorships",
                runner=ingest_lattes_advisorships_flow,
                source_probe=probe_lattes_advisorships,
            )
        else:
            ingest_lattes_advisorships_flow()

        logger.info(f"Step 6/8: Syncing CNPq groups (Filter: {campus_name or 'None'})...")
        if reporter:
            reporter.run_step(
                step_name="cnpq_sync",
                runner=lambda: sync_cnpq_groups_flow(campus_name=campus_name),
                source_probe=lambda: probe_cnpq_sync(campus_name),
            )
        else:
            sync_cnpq_groups_flow(campus_name=campus_name)

        logger.info(f"Step 7/8: Exporting canonical data to {output_dir}...")
        export_canonical_data_flow(output_dir=output_dir, campus=campus_name)

        ka_mart_path = os.path.join(output_dir, "knowledge_areas_mart.json")
        logger.info(f"Step 8/8: Generating marts at {output_dir}...")
        export_knowledge_areas_mart_flow(output_path=ka_mart_path, campus=campus_name)

        analytics_mart_path = os.path.join(output_dir, "initiatives_analytics_mart.json")
        export_initiatives_analytics_mart_flow(output_path=analytics_mart_path)
        logger.info("Unified Ingestion Pipeline completed successfully.")
    finally:
        if reporter:
            json_path, md_path = reporter.write()
            logger.info(
                f"ETL execution report written to {json_path} and {md_path}. "
                "Latest aliases updated in data/reports/etl_flow_run.json and "
                "data/reports/etl_flow_run.md"
            )


if __name__ == "__main__":
    full_ingestion_pipeline()

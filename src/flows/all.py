from typing import Optional

from prefect import flow, get_run_logger

from src.flows.cnpq.groups import sync_cnpq_groups_flow
from src.flows.lattes.complete import lattes_complete_flow
from src.flows.sigpesq.all import ingest_sigpesq_flow
from src.notifications.telegram import telegram_flow_state_handlers


@flow(name="Ingest All Sources", **telegram_flow_state_handlers())
def ingest_all_sources_flow(campus_name: Optional[str] = None) -> None:
    """
    Run all source ingestion flows.

    Sources are intentionally separated from export/mart flows so the caller can
    decide whether this run is ingestion-only or a full pipeline with outputs.
    """
    logger = get_run_logger()
    logger.info("Starting all source ingestion flows.")

    ingest_sigpesq_flow()
    sync_cnpq_groups_flow(campus_name=campus_name)
    lattes_complete_flow()

    logger.info("All source ingestion flows finished successfully.")


if __name__ == "__main__":
    ingest_all_sources_flow()

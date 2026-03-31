"""Prefect runtime tweaks for local CLI ETL execution."""

from src.prefect_runtime import (
    disable_prefect_events_client,
    patch_prefect_task_run_payloads,
)

_configured = False


def configure_local_prefect_runtime() -> None:
    """Disable Prefect event streaming noise for local ETL runs."""
    global _configured

    if _configured:
        return

    patch_prefect_task_run_payloads()
    disable_prefect_events_client()
    _configured = True

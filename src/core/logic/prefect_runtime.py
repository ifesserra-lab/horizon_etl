"""Prefect runtime tweaks for local CLI ETL execution."""

from prefect.events.clients import NullEventsClient
from prefect.events.worker import EventsWorker

_configured = False


def configure_local_prefect_runtime() -> None:
    """Disable Prefect event streaming noise for local ETL runs."""
    global _configured

    if _configured:
        return

    EventsWorker.set_client_override(NullEventsClient)
    _configured = True

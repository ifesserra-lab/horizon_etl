import os


def bootstrap_local_prefect() -> None:
    """Disable noisy Prefect API side channels for local CLI runs."""

    if os.getenv("HORIZON_QUIET_PREFECT") not in {"1", "true", "TRUE"}:
        return

    os.environ.setdefault("PREFECT_LOGGING_TO_API_ENABLED", "false")
    os.environ.setdefault("PREFECT_CLIENT_SERVER_VERSION_CHECK_ENABLED", "false")

    try:
        import prefect.events.utilities as events_utilities
        import prefect.events.worker as events_worker
        from prefect.events.clients import NullEventsClient

        events_worker.should_emit_events = lambda: False
        events_utilities.should_emit_events = lambda: False
        events_worker.EventsWorker.set_client_override(NullEventsClient)
    except Exception:
        # Local ETL execution should proceed even if Prefect internals change.
        pass

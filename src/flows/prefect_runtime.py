import os
from urllib.parse import urlparse


def configure_prefect_runtime() -> bool:
    """Disable Prefect event streaming for local runs without API auth.

    Local `make full-refresh` runs use a Prefect API URL for orchestration and UI,
    but the events websocket may not be authenticated. In that case Prefect emits
    noisy warnings/errors for every state transition. We keep orchestration
    enabled and only replace the events client with a no-op implementation.
    """

    try:
        from prefect.events.clients import NullEventsClient
        from prefect.events.worker import EventsWorker
        from prefect.settings import PREFECT_API_KEY, PREFECT_API_URL
    except Exception:
        return False

    api_url = os.getenv("PREFECT_API_URL") or PREFECT_API_URL.value()
    api_key = os.getenv("PREFECT_API_KEY") or PREFECT_API_KEY.value()

    if not api_url or api_key:
        return False

    hostname = urlparse(str(api_url)).hostname or ""
    if hostname not in {"127.0.0.1", "localhost"}:
        return False

    EventsWorker.set_client_override(NullEventsClient)
    return True

from unittest.mock import patch

from prefect.events.clients import NullEventsClient

from src.flows.prefect_runtime import configure_prefect_runtime


def test_configure_prefect_runtime_disables_events_for_local_server(monkeypatch):
    monkeypatch.setenv("PREFECT_API_URL", "http://127.0.0.1:4200/api")
    monkeypatch.delenv("PREFECT_API_KEY", raising=False)

    with patch("prefect.events.worker.EventsWorker.set_client_override") as override:
        assert configure_prefect_runtime() is True
        override.assert_called_once_with(NullEventsClient)


def test_configure_prefect_runtime_keeps_events_for_non_local_urls(monkeypatch):
    monkeypatch.setenv("PREFECT_API_URL", "https://api.prefect.cloud/api/accounts/x/workspaces/y")
    monkeypatch.delenv("PREFECT_API_KEY", raising=False)

    with patch("prefect.events.worker.EventsWorker.set_client_override") as override:
        assert configure_prefect_runtime() is False
        override.assert_not_called()


def test_configure_prefect_runtime_keeps_events_when_api_key_is_present(monkeypatch):
    monkeypatch.setenv("PREFECT_API_URL", "http://127.0.0.1:4200/api")
    monkeypatch.setenv("PREFECT_API_KEY", "token")

    with patch("prefect.events.worker.EventsWorker.set_client_override") as override:
        assert configure_prefect_runtime() is False
        override.assert_not_called()

from types import SimpleNamespace
from urllib.parse import parse_qs


def test_telegram_flow_hook_sends_completion_report(monkeypatch):
    from src.notifications.telegram import notify_telegram_flow_finished

    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setenv("HORIZON_TELEGRAM_BOT_TOKEN", "token-123")
    monkeypatch.setenv("HORIZON_TELEGRAM_CHAT_ID", "-100123")
    monkeypatch.setenv("PREFECT_API_URL", "http://127.0.0.1:4200/api")
    monkeypatch.setattr("src.notifications.telegram.urlopen", fake_urlopen)

    flow = SimpleNamespace(name="Ingest SigPesq Full")
    flow_run = SimpleNamespace(
        id="run-123",
        name="talkative-deer",
        parameters={"campus_name": "Serra"},
    )
    state = SimpleNamespace(type="COMPLETED", name="Completed", message="All good")

    assert notify_telegram_flow_finished(flow, flow_run, state) is True

    request, timeout = requests[0]
    assert timeout == 10
    assert request.full_url == "https://api.telegram.org/bottoken-123/sendMessage"

    payload = parse_qs(request.data.decode())
    assert payload["chat_id"] == ["-100123"]
    assert "Horizon ETL flow report" in payload["text"][0]
    assert "Flow: Ingest SigPesq Full" in payload["text"][0]
    assert "State: Completed" in payload["text"][0]
    assert "Finished at:" in payload["text"][0]
    assert "Run URL: http://127.0.0.1:4200/runs/flow-run/run-123" in payload["text"][0]


def test_telegram_flow_hook_sends_start_report(monkeypatch):
    from src.notifications.telegram import notify_telegram_flow_started

    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setenv("HORIZON_TELEGRAM_BOT_TOKEN", "token-123")
    monkeypatch.setenv("HORIZON_TELEGRAM_CHAT_ID", "-100123")
    monkeypatch.setattr("src.notifications.telegram.urlopen", fake_urlopen)

    flow = SimpleNamespace(name="Weekly Pipelines")
    flow_run = SimpleNamespace(id="run-001", name="steady-run", parameters={})
    state = SimpleNamespace(type="RUNNING", name="Running", message=None)

    assert notify_telegram_flow_started(flow, flow_run, state) is True

    payload = parse_qs(requests[0][0].data.decode())
    assert "Horizon ETL flow started" in payload["text"][0]
    assert "Flow: Weekly Pipelines" in payload["text"][0]
    assert "State: Running" in payload["text"][0]
    assert "Started at:" in payload["text"][0]


def test_telegram_report_summary_sends_final_totals(monkeypatch):
    from src.notifications.telegram import send_telegram_etl_report_summary

    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setenv("HORIZON_TELEGRAM_BOT_TOKEN", "token-123")
    monkeypatch.setenv("HORIZON_TELEGRAM_CHAT_ID", "-100123")
    monkeypatch.setattr("src.notifications.telegram.urlopen", fake_urlopen)

    report = {
        "run_name": "weekly_pipeline_run",
        "started_at": "2026-04-19T10:00:00",
        "finished_at": "2026-04-19T10:15:00",
        "steps": [
            {
                "step_name": "all_sources",
                "status": "success",
                "duration_seconds": 10.5,
                "saved_entities": [
                    {"entity": "research_groups", "delta": 3},
                    {"entity": "initiatives", "delta": 7},
                ],
                "extracted_counts": {"files": 2},
            },
            {
                "step_name": "exports",
                "status": "failed",
                "duration_seconds": 2.0,
                "error": "boom",
                "saved_entities": [],
                "extracted_counts": {},
            },
        ],
        "final_tables": {"research_groups": 3, "initiatives": 7},
        "final_duplicates": {"persons": 1, "research_groups": 0},
        "warnings_by_source": {
            "cnpq": [
                {
                    "code": "cnpq_placeholder_member_name",
                    "message": "Found placeholder member names.",
                    "count": 2,
                }
            ],
            "duplicate_audit": [
                {
                    "code": "duplicate_count_present",
                    "message": "Duplicate groups remain.",
                    "count": 1,
                }
            ],
        },
        "tracking_summary": {
            "enabled": True,
            "totals": {"ingestion_runs": 2, "source_records": 10},
        },
    }

    assert send_telegram_etl_report_summary(report) is True

    payload = parse_qs(requests[0][0].data.decode())
    text = payload["text"][0]
    assert "Horizon ETL final report" in text
    assert "Run: weekly_pipeline_run" in text
    assert "Steps: 1 success, 1 failed" in text
    assert "Saved deltas: initiatives=7, research_groups=3" in text
    assert "Final duplicates: persons=1, research_groups=0" in text
    assert "Warnings: cnpq=1, duplicate_audit=1" in text
    assert "Tracking: ingestion_runs=2, source_records=10" in text
    assert "Failed steps: exports" in text


def test_telegram_flow_hook_skips_when_credentials_are_missing(monkeypatch):
    from src.notifications.telegram import notify_telegram_flow_finished

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("HORIZON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("HORIZON_TELEGRAM_CHAT_ID", raising=False)

    def fail_urlopen(_request, _timeout):
        raise AssertionError("urlopen should not be called")

    monkeypatch.setattr("src.notifications.telegram.urlopen", fail_urlopen)

    flow = SimpleNamespace(name="Any Flow")
    flow_run = SimpleNamespace(id="run-456", name="run-name", parameters={})
    state = SimpleNamespace(type="FAILED", name="Failed", message="boom")

    assert notify_telegram_flow_finished(flow, flow_run, state) is False


def test_telegram_flow_hook_does_not_fail_flow_when_send_fails(monkeypatch):
    from src.notifications.telegram import notify_telegram_flow_finished

    monkeypatch.setenv("HORIZON_TELEGRAM_BOT_TOKEN", "token-123")
    monkeypatch.setenv("HORIZON_TELEGRAM_CHAT_ID", "-100123")

    def fail_urlopen(_request, timeout):
        raise TimeoutError("telegram timeout")

    monkeypatch.setattr("src.notifications.telegram.urlopen", fail_urlopen)

    flow = SimpleNamespace(name="Any Flow")
    flow_run = SimpleNamespace(id="run-789", name="run-name", parameters={})
    state = SimpleNamespace(type="COMPLETED", name="Completed", message=None)

    assert notify_telegram_flow_finished(flow, flow_run, state) is False


def test_top_level_flows_register_telegram_completion_hooks():
    from src.flows.all import ingest_all_sources_flow
    from src.flows.cnpq.groups import sync_cnpq_groups_flow
    from src.flows.exports.canonical_data import export_canonical_data_flow
    from src.flows.exports.initiatives_analytics_mart import (
        export_initiatives_analytics_mart_flow,
    )
    from src.flows.exports.knowledge_areas_mart import export_knowledge_areas_mart_flow
    from src.flows.exports.people_relationship_graph import (
        export_people_relationship_graph_flow,
    )
    from src.flows.lattes.advisorships import ingest_lattes_advisorships_flow
    from src.flows.lattes.complete import lattes_complete_flow
    from src.flows.lattes.complete_projects import (
        lattes_complete_flow as lattes_complete_projects_flow,
    )
    from src.flows.lattes.download import download_lattes_flow
    from src.flows.lattes.projects import ingest_lattes_projects_flow
    from src.flows.pipelines.unified import full_ingestion_pipeline
    from src.flows.pipelines.weekly import weekly_pipelines_flow
    from src.flows.sigpesq.advisorships import ingest_advisorships_flow
    from src.flows.sigpesq.all import ingest_sigpesq_flow
    from src.flows.sigpesq.groups import ingest_research_groups_flow
    from src.flows.sigpesq.projects import ingest_projects_flow
    from src.notifications.telegram import (
        notify_telegram_flow_finished,
        notify_telegram_flow_started,
    )

    flows = [
        ingest_all_sources_flow,
        sync_cnpq_groups_flow,
        export_canonical_data_flow,
        export_initiatives_analytics_mart_flow,
        export_knowledge_areas_mart_flow,
        export_people_relationship_graph_flow,
        ingest_lattes_advisorships_flow,
        lattes_complete_flow,
        lattes_complete_projects_flow,
        download_lattes_flow,
        ingest_lattes_projects_flow,
        full_ingestion_pipeline,
        weekly_pipelines_flow,
        ingest_advisorships_flow,
        ingest_sigpesq_flow,
        ingest_research_groups_flow,
        ingest_projects_flow,
    ]

    for flow in flows:
        assert flow.on_running_hooks == [notify_telegram_flow_started]
        assert flow.on_completion_hooks == [notify_telegram_flow_finished]
        assert flow.on_failure_hooks == [notify_telegram_flow_finished]
        assert flow.on_crashed_hooks == [notify_telegram_flow_finished]
        assert flow.on_cancellation_hooks == [notify_telegram_flow_finished]

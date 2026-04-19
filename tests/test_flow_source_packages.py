from pathlib import Path
from unittest.mock import MagicMock, patch


def test_source_flow_packages_expose_source_entrypoints():
    from src.flows.cnpq.groups import sync_cnpq_groups_flow
    from src.flows.lattes.complete import lattes_complete_flow
    from src.flows.sigpesq.all import ingest_sigpesq_flow

    assert ingest_sigpesq_flow is not None
    assert lattes_complete_flow is not None
    assert sync_cnpq_groups_flow is not None


def test_all_sources_flow_orchestrates_each_source():
    from src.flows.all import ingest_all_sources_flow

    logger = MagicMock()
    with (
        patch("src.flows.all.get_run_logger", return_value=logger),
        patch("src.flows.all.ingest_sigpesq_flow") as sigpesq_flow,
        patch("src.flows.all.lattes_complete_flow") as lattes_flow,
        patch("src.flows.all.sync_cnpq_groups_flow") as cnpq_flow,
    ):
        ingest_all_sources_flow.fn(campus_name="Serra")

    sigpesq_flow.assert_called_once_with()
    lattes_flow.assert_called_once_with()
    cnpq_flow.assert_called_once_with(campus_name="Serra")


def test_flow_root_does_not_keep_flat_compatibility_wrappers():
    flow_root = Path("src/flows")
    flat_wrappers = {
        "download_lattes.py",
        "export_canonical_data.py",
        "export_initiatives_analytics_mart.py",
        "export_knowledge_areas_mart.py",
        "export_people_relationship_graph.py",
        "ingest_lattes_advisorships.py",
        "ingest_lattes_projects.py",
        "ingest_sigpesq.py",
        "ingest_sigpesq_advisorships.py",
        "ingest_sigpesq_groups.py",
        "ingest_sigpesq_projects.py",
        "lattes_complete.py",
        "lattes_complete_flow.py",
        "run_serra_pipeline.py",
        "sync_cnpq_groups.py",
        "unified_pipeline.py",
    }

    existing_wrappers = sorted(
        path.name for path in flow_root.glob("*.py") if path.name in flat_wrappers
    )

    assert existing_wrappers == []

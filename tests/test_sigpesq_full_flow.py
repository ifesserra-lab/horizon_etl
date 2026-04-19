from unittest.mock import MagicMock, patch


def test_sigpesq_full_flow_downloads_all_reports_with_single_login():
    from src.flows.sigpesq.all import ingest_sigpesq_flow

    with (
        patch("src.flows.sigpesq.all.get_run_logger", return_value=MagicMock()),
        patch("src.flows.sigpesq.all.SigPesqAdapter", create=True) as adapter_cls,
        patch(
            "src.flows.sigpesq.all.ResearchGroupsDownloadStrategy", create=True
        ) as groups_strategy_cls,
        patch(
            "src.flows.sigpesq.all.ProjectsDownloadStrategy", create=True
        ) as projects_strategy_cls,
        patch(
            "src.flows.sigpesq.all.AdvisorshipsDownloadStrategy", create=True
        ) as advisorships_strategy_cls,
        patch("src.flows.sigpesq.all.persist_research_groups", create=True) as persist_groups,
        patch("src.flows.sigpesq.all.persist_projects", create=True) as persist_projects,
        patch("src.flows.sigpesq.all.persist_advisorships", create=True) as persist_advisorships,
        patch(
            "src.flows.sigpesq.all.ingest_research_groups_flow", create=True
        ) as groups_flow,
        patch("src.flows.sigpesq.all.ingest_projects_flow", create=True) as projects_flow,
        patch(
            "src.flows.sigpesq.all.ingest_advisorships_flow", create=True
        ) as advisorships_flow,
    ):
        ingest_sigpesq_flow.fn()

    adapter_cls.assert_called_once_with()
    adapter_cls.return_value.extract.assert_called_once_with(
        download_strategies=[
            groups_strategy_cls.return_value,
            projects_strategy_cls.return_value,
            advisorships_strategy_cls.return_value,
        ]
    )
    persist_groups.assert_called_once_with()
    persist_projects.assert_called_once_with()
    persist_advisorships.assert_called_once_with()
    groups_flow.assert_not_called()
    projects_flow.assert_not_called()
    advisorships_flow.assert_not_called()

from unittest.mock import patch

from src.flows.export_canonical_data import export_canonical_data_flow


def test_export_canonical_data_flow_calls_tracking_exports_individually(tmp_path):
    output_dir = str(tmp_path / "exports")

    with (
        patch("src.flows.export_canonical_data.export_organizations_task") as organizations_task,
        patch("src.flows.export_canonical_data.export_campuses_task") as campuses_task,
        patch("src.flows.export_canonical_data.export_knowledge_areas_task") as knowledge_areas_task,
        patch("src.flows.export_canonical_data.export_researchers_task") as researchers_task,
        patch("src.flows.export_canonical_data.export_researchers_tracking_task") as researchers_tracking_task,
        patch("src.flows.export_canonical_data.export_groups_task") as groups_task,
        patch("src.flows.export_canonical_data.export_initiatives_task") as initiatives_task,
        patch("src.flows.export_canonical_data.export_initiatives_tracking_task") as initiatives_tracking_task,
        patch("src.flows.export_canonical_data.export_initiative_types_task") as initiative_types_task,
        patch("src.flows.export_canonical_data.export_articles_task") as articles_task,
        patch("src.flows.export_canonical_data.export_advisorships_task") as advisorships_task,
        patch("src.flows.export_canonical_data.export_advisorships_tracking_task") as advisorships_tracking_task,
        patch("src.flows.export_canonical_data.export_ingestion_runs_task") as ingestion_runs_task,
        patch("src.flows.export_canonical_data.export_source_records_task") as source_records_task,
        patch("src.flows.export_canonical_data.export_entity_matches_task") as entity_matches_task,
        patch("src.flows.export_canonical_data.export_attribute_assertions_task") as attribute_assertions_task,
        patch("src.flows.export_canonical_data.export_entity_change_logs_task") as entity_change_logs_task,
        patch("src.flows.export_canonical_data.export_fellowships_task") as fellowships_task,
        patch("src.flows.export_canonical_data.export_advisorship_analytics_task") as advisorship_analytics_task,
        patch("os.makedirs") as makedirs,
    ):
        export_canonical_data_flow(output_dir=output_dir, campus="Serra")

    makedirs.assert_called_once_with(output_dir, exist_ok=True)
    organizations_task.assert_called_once_with(output_dir)
    campuses_task.assert_called_once_with(output_dir, "Serra")
    knowledge_areas_task.assert_called_once_with(output_dir)
    researchers_task.assert_called_once_with(output_dir)
    researchers_tracking_task.assert_called_once_with(output_dir)
    groups_task.assert_called_once_with(output_dir, "Serra")
    initiatives_task.assert_called_once_with(output_dir)
    initiatives_tracking_task.assert_called_once_with(output_dir)
    initiative_types_task.assert_called_once_with(output_dir)
    articles_task.assert_called_once_with(output_dir)
    advisorships_task.assert_called_once_with(output_dir)
    advisorships_tracking_task.assert_called_once_with(output_dir)
    ingestion_runs_task.assert_called_once_with(output_dir)
    source_records_task.assert_called_once_with(output_dir)
    entity_matches_task.assert_called_once_with(output_dir)
    attribute_assertions_task.assert_called_once_with(output_dir)
    entity_change_logs_task.assert_called_once_with(output_dir)
    fellowships_task.assert_called_once_with(output_dir)
    advisorship_analytics_task.assert_called_once_with(output_dir)

from unittest.mock import patch

from src.flows.export_people_relationship_graph import (
    export_people_relationship_graph_flow,
    generate_people_relationship_graph_task,
)


def test_export_people_relationship_graph_flow_calls_generator_with_expected_paths(
    tmp_path,
):
    output_dir = str(tmp_path / "exports")

    with patch(
        "src.flows.export_people_relationship_graph.generate_people_relationship_graph_task"
    ) as mock_task:
        export_people_relationship_graph_flow.fn(output_dir=output_dir)

    mock_task.assert_called_once_with(output_dir)


def test_generate_people_relationship_graph_task_calls_generator_bundle(tmp_path):
    output_dir = str(tmp_path / "exports")

    with patch(
        "src.flows.export_people_relationship_graph.PeopleRelationshipGraphGenerator"
    ) as mock_generator_class, patch(
        "src.flows.export_people_relationship_graph.get_run_logger"
    ):
        generate_people_relationship_graph_task.fn(output_dir)

    mock_generator_class.return_value.generate_all.assert_called_once_with(
        researchers_path=f"{output_dir}/researchers_canonical.json",
        initiatives_path=f"{output_dir}/initiatives_canonical.json",
        research_groups_path=f"{output_dir}/research_groups_canonical.json",
        advisorships_path=f"{output_dir}/advisorships_canonical.json",
        output_dir=output_dir,
    )

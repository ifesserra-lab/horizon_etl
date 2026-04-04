import os

from prefect import flow, get_run_logger, task

from src.core.logic.people_relationship_graph_generator import (
    PeopleRelationshipGraphGenerator,
)


@task(name="generate_people_relationship_graph_task")
def generate_people_relationship_graph_task(output_dir: str):
    logger = get_run_logger()
    logger.info(
        "Starting People Relationship Graph bundle generation from canonical exports in {}...",
        output_dir,
    )

    generator = PeopleRelationshipGraphGenerator()
    export_summary = generator.generate_all(
        researchers_path=os.path.join(output_dir, "researchers_canonical.json"),
        initiatives_path=os.path.join(output_dir, "initiatives_canonical.json"),
        research_groups_path=os.path.join(output_dir, "research_groups_canonical.json"),
        advisorships_path=os.path.join(output_dir, "advisorships_canonical.json"),
        output_dir=output_dir,
    )

    logger.info(
        "People Relationship Graph bundle completed. Full relationship graph at {}, full collaboration graph at {}, {} collaboration research-group graph files generated, and {} membership research-group graph files generated.",
        export_summary["full_graph_path"],
        export_summary["collaboration_graph_path"],
        len(export_summary["research_group_exports"]["graphs"]),
        len(export_summary["research_group_membership_exports"]["graphs"]),
    )


@flow(name="Export People Relationship Graph Flow")
def export_people_relationship_graph_flow(output_dir: str = "data/exports"):
    """
    Flow to generate the people relationship graph JSON from canonical exports.

    Args:
        output_dir: Directory containing the canonical exports and where the graph
            JSON will be saved.
    """
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.getcwd(), output_dir)

    generate_people_relationship_graph_task(output_dir)


if __name__ == "__main__":
    export_people_relationship_graph_flow()

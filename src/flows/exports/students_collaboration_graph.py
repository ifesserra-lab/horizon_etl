import os

from prefect import flow, get_run_logger, task

from src.core.logic.students_collaboration_graph_generator import (
    StudentsCollaborationGraphGenerator,
)
from src.notifications.telegram import telegram_flow_state_handlers


@task(name="generate_students_collaboration_graph_task")
def generate_students_collaboration_graph_task(output_dir: str):
    logger = get_run_logger()
    output_path = os.path.join(output_dir, "students_collaboration_graph.json")
    logger.info("Generating Students Collaboration Graph → %s", output_path)

    generator = StudentsCollaborationGraphGenerator()
    result = generator.generate(
        researchers_path=os.path.join(output_dir, "researchers_canonical.json"),
        output_path=output_path,
    )

    logger.info(
        "Students Collaboration Graph completed: %d nodes, %d edges.",
        result["graph_stats"]["nodes"],
        result["graph_stats"]["edges"],
    )


@flow(name="Export Students Collaboration Graph Flow", **telegram_flow_state_handlers())
def export_students_collaboration_graph_flow(output_dir: str = "data/exports"):
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.getcwd(), output_dir)

    generate_students_collaboration_graph_task(output_dir)


if __name__ == "__main__":
    export_students_collaboration_graph_flow()

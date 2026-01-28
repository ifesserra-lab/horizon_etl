import os
from typing import Optional

from loguru import logger
from prefect import flow, task

from src.adapters.sinks.json_sink import JsonSink
from src.core.logic.canonical_exporter import CanonicalDataExporter
from src.core.logic.research_group_exporter import ResearchGroupExporter


@task(name="export_organizations_task")
def export_organizations_task(output_dir: str):
    logger.info("Starting Organizations export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_organizations(
        os.path.join(output_dir, "organizations_canonical.json")
    )


@task(name="export_campuses_task")
def export_campuses_task(output_dir: str, campus: Optional[str] = None):
    logger.info("Starting Campuses export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_campuses(
        os.path.join(output_dir, "campuses_canonical.json"), campus_filter=campus
    )


@task(name="export_knowledge_areas_task")
def export_knowledge_areas_task(output_dir: str):
    logger.info("Starting Knowledge Areas export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_knowledge_areas(
        os.path.join(output_dir, "knowledge_areas_canonical.json")
    )


@task(name="export_researchers_task")
def export_researchers_task(output_dir: str):
    logger.info("Starting Researchers export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_researchers(os.path.join(output_dir, "researchers_canonical.json"))


@task(name="export_groups_task")
def export_groups_task(output_dir: str, campus: Optional[str] = None):
    output_path = os.path.join(output_dir, "research_groups_canonical.json")
    logger.info(
        f"Starting Research Groups export to {output_path} (Filter: {campus})..."
    )
    sink = JsonSink()
    exporter = ResearchGroupExporter(sink=sink)
    exporter.export_all(output_path, campus_filter=campus)


@task(name="export_initiatives_task")
def export_initiatives_task(output_dir: str):
    logger.info("Starting Initiatives export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_initiatives(os.path.join(output_dir, "initiatives_canonical.json"))


@task(name="export_initiative_types_task")
def export_initiative_types_task(output_dir: str):
    logger.info("Starting Initiative Types export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_initiative_types(
        os.path.join(output_dir, "initiative_types_canonical.json")
    )


@task(name="export_advisorships_task")
def export_advisorships_task(output_dir: str):
    logger.info("Starting Advisorships export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_advisorships(os.path.join(output_dir, "advisorships_canonical.json"))


@task(name="export_fellowships_task")
def export_fellowships_task(output_dir: str):
    logger.info("Starting Fellowships export...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    exporter.export_fellowships(os.path.join(output_dir, "fellowships_canonical.json"))


@task(name="export_advisorship_analytics_task")
def export_advisorship_analytics_task(output_dir: str):
    logger.info("Starting Advisorship Analytics Mart generation...")
    sink = JsonSink()
    exporter = CanonicalDataExporter(sink=sink)
    input_path = os.path.join(output_dir, "advisorships_canonical.json")
    output_path = os.path.join(output_dir, "advisorship_analytics.json")
    exporter.generate_advisorship_mart(input_path, output_path)


@flow(name="Export Canonical Data Flow")
def export_canonical_data_flow(
    output_dir: str = "data/exports", campus: Optional[str] = None
):
    """
    Flow to export canonical data (Organizations, Campuses, Knowledge Areas, Researchers)
    AND Research Groups to JSON files.

    Args:
        output_dir: Directory where the JSON files will be saved. Defaults to 'data/exports'.
        campus: Optional name of the campus to filter by.
    """
    # Ensure absolute path or relative to CWD
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.getcwd(), output_dir)

    os.makedirs(output_dir, exist_ok=True)

    # Run tasks in parallel or sequence
    export_organizations_task(output_dir)
    export_campuses_task(output_dir, campus)
    export_knowledge_areas_task(output_dir)
    export_researchers_task(output_dir)
    export_groups_task(output_dir, campus)
    export_initiatives_task(output_dir)
    export_initiative_types_task(output_dir)
    export_advisorships_task(output_dir)
    export_fellowships_task(output_dir)
    export_advisorship_analytics_task(output_dir)


if __name__ == "__main__":
    export_canonical_data_flow()

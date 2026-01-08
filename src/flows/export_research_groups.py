from prefect import flow, task
from typing import Optional
from loguru import logger
import os

from src.core.logic.research_group_exporter import ResearchGroupExporter
from src.adapters.sinks.json_sink import JsonSink

@task(name="export_groups_task")
def export_groups_task(output_path: str):
    logger.info(f"Starting export task. Destination: {output_path}")
    sink = JsonSink()
    exporter = ResearchGroupExporter(sink=sink)
    exporter.export_all(output_path)

@flow(name="Export Research Groups Flow")
def export_research_groups_flow(output_path: str = "data/exports/research_groups.json"):
    """
    Flow to export all Research Groups to a JSON file.
    
    Args:
        output_path: Path to save the JSON file. Defaults to 'data/exports/research_groups.json'.
    """
    # Ensure absolute path or relative to CWD
    if not os.path.isabs(output_path):
        output_path = os.path.join(os.getcwd(), output_path)
        
    export_groups_task(output_path)

if __name__ == "__main__":
    export_research_groups_flow()

from datetime import timedelta
from typing import Any, Dict, List

from prefect import flow, task, get_run_logger
from dotenv import load_dotenv

from src.adapters.sources.sigpesq.adapter import SigPesqAdapter
from src.core.logic.loaders import SigPesqFileLoader
from src.core.logic.mappers import SigPesqMapper
from src.core.logic.research_group_loader import ResearchGroupLoader
from src.core.logic.strategies.sigpesq_excel import (
    SigPesqExcelMappingStrategy,
    SigPesqOrganizationStrategy,
    SigPesqCampusStrategy,
    SigPesqKnowledgeAreaStrategy,
    SigPesqResearcherStrategy,
    SigPesqRoleStrategy
)
from src.core.ports.sink import ISink
load_dotenv()


@task
def extract_data() -> List[dict]:
    """
    Extracts raw data from SigPesq using the configured adapter.

    Returns:
        List[dict]: A list of raw data dictionaries containing 'filename' and 'parsed_content'.
    """
    logger = get_run_logger()
    logger.info("Starting extraction task...")
    
    # Import strategies locally to avoid top-level dependency issues if lib is missing
    from agent_sigpesq.strategies import ResearchGroupsDownloadStrategy, ProjectsDownloadStrategy
    
    adapter = SigPesqAdapter()
    
    # Download both Groups and Projects
    raw_data = adapter.extract(download_strategies=[
        ResearchGroupsDownloadStrategy(),
        ProjectsDownloadStrategy()
    ])
    logger.info(f"Extracted {len(raw_data)} items.")
    return raw_data


@task
def transform_data(raw_data: List[dict]) -> List[Any]:
    """
    Transforms raw SigPesq data into domain entities.

    Args:
        raw_data (List[dict]): The raw data extracted from SigPesq.

    Returns:
        List[Any]: A list of domain entities (Project, ResearchGroup, Researcher).
    """
    logger = get_run_logger()
    logger.info("Starting transformation task...")

    entities = []
    for item in raw_data:
        try:
            # item structure from SigPesqFileLoader: {'filename': ..., 'parsed_content': ...}
            content = item.get("parsed_content", {})
            filename = item.get("filename", "")

            # Heuristic to determine type
            # Real implementation should rely on specific file structure or metadata
            entity = None

            if "titulo" in content:
                logger.debug(f"Mapping Project from {filename}")
                entity = SigPesqMapper.map_project(content)

            elif "nome_grupo" in content:
                logger.debug(f"Mapping ResearchGroup from {filename}")
                entity = SigPesqMapper.map_research_group(content)

            elif "nome" in content and "funcao" in content:
                logger.debug(f"Mapping Researcher from {filename}")
                entity = SigPesqMapper.map_researcher(content)

            if entity:
                entities.append(entity)
            else:
                logger.warning(f"Could not determine entity type for {filename}")

        except Exception as e:
            logger.error(f"Failed to transform item {item.get('filename')}: {e}")

    logger.info(f"Transformation complete. Mapped {len(entities)} entities.")
    return entities


@task
def persist_data(entities: List[Any]) -> None:
    """
    Persists domain entities to the configured sink (e.g., Database).

    Args:
        entities (List[Any]): The list of domain entities to persist.
    """
    logger = get_run_logger()
    logger.info(f"Persisting {len(entities)} entities...")

    # Placeholder for Persistence Layer (Repository)
    # In real scenario: repo.save(entity)
    for entity in entities:
        logger.info(f"Persisted: {entity}")

    logger.info("Persistence complete.")


@task
def persist_research_groups():
    """
    Finds the latest Research Group Excel file and loads it into the database.
    """
    logger = get_run_logger()
    import glob
    import os
    
    # Find latest file
    files = glob.glob("data/raw/sigpesq/research_group/*.xlsx")
    if not files:
        logger.warning("No Research Group Excel files found.")
        return

    # Sort by mtime
    latest_file = max(files, key=os.path.getmtime)
    logger.info(f"Loading Research Groups from {latest_file}")
    
    loader = ResearchGroupLoader(
        mapping_strategy=SigPesqExcelMappingStrategy(),
        org_strategy=SigPesqOrganizationStrategy(),
        campus_strategy=SigPesqCampusStrategy(),
        area_strategy=SigPesqKnowledgeAreaStrategy(),
        researcher_strategy=SigPesqResearcherStrategy(),
        role_strategy=SigPesqRoleStrategy()
    )
    loader.process_file(latest_file)


@task
def persist_projects():
    """
    Finds the latest Projects Excel file and loads it into the database as Initiatives.
    """
    logger = get_run_logger()
    import glob
    import os
    from src.core.logic.project_loader import ProjectLoader
    from src.core.logic.strategies.sigpesq_projects import SigPesqProjectMappingStrategy
    
    # Find latest file
    # Assuming 'projects' or similar folder structure from agent_sigpesq
    # ProjectsDownloadStrategy usually saves to 'research_project' or similar. 
    # I'll check/search for the folder or use a glob pattern matching expected output.
    # Default agent_sigpesq strategies: ResearchGroups -> "research_group", Projects -> "research_project"
    
    files = glob.glob("data/raw/sigpesq/research_project/*.xlsx")
    if not files:
        logger.warning("No Project Excel files found in data/raw/sigpesq/research_project/.")
        return

    # Sort by mtime
    latest_file = max(files, key=os.path.getmtime)
    logger.info(f"Loading Projects from {latest_file}")
    
    loader = ProjectLoader(
        mapping_strategy=SigPesqProjectMappingStrategy()
    )
    loader.process_file(latest_file)


@flow(name="Ingest SigPesq")
def ingest_sigpesq_flow() -> None:
    """
    Main Prefect Flow for ingesting SigPesq data.

    Orchestrates the Extraction, Transformation, and Loading (ETL) process.
    """
    logger = get_run_logger()
    logger.info("Initializing SigPesq Ingestion Flow")

    raw_data = extract_data()
    entities = transform_data(raw_data)
    persist_data(entities)
    
    # Ingest Research Groups from Excel (US-007)
    persist_research_groups()
    
    # Ingest Projects from Excel (New Initiative Flow)
    persist_projects()

    logger.info("Flow finished successfully.")


if __name__ == "__main__":
    ingest_sigpesq_flow()

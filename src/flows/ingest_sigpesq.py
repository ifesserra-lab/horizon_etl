
from typing import Any, List

from dotenv import load_dotenv
from prefect import flow, get_run_logger, task

from src.adapters.sources.sigpesq.adapter import SigPesqAdapter
from src.core.logic.mappers import SigPesqMapper

# Load environment variables from .env file
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
    adapter = SigPesqAdapter()
    raw_data = adapter.extract()
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

    logger.info("Flow finished successfully.")


if __name__ == "__main__":
    ingest_sigpesq_flow()

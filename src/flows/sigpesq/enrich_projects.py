from dotenv import load_dotenv
from prefect import flow, get_run_logger

from src.core.logic.project_enrichment import ProjectEnrichmentLoader
from src.notifications.telegram import telegram_flow_state_handlers
from src.tracking.recorder import tracking_recorder

load_dotenv()

DEFAULT_PJ_DIR = "data/exports/project_sigpesq_files_json"


@flow(name="Enrich SigPesq Projects", **telegram_flow_state_handlers())
def enrich_projects_flow(
    pj_dir: str = DEFAULT_PJ_DIR,
    overwrite: bool = False,
    dry_run: bool = False,
    ingest_new: bool = False,
) -> dict:
    """
    Enriches Research Project initiatives already in the database with content
    extracted from the SigPesq project document files (``PJ_*.json``).

    Fills empty descriptions and stores the richer document fields (objectives,
    schedule, research line, keywords) in ``initiatives.enrichment_json``. Only
    projects that already map to an existing Research Project initiative are
    touched; the code-matched ones are approved projects, title/fuzzy matches are
    flagged for review inside the enrichment payload.
    """
    logger = get_run_logger()
    logger.info("Initializing SigPesq Project Enrichment Flow")

    loader = ProjectEnrichmentLoader(overwrite=overwrite, dry_run=dry_run)

    def _run():
        result = {"enrichment": loader.load(pj_dir)}
        if ingest_new:
            result["ingest"] = loader.ingest_unmatched(pj_dir)
        return result

    if dry_run:
        stats = _run()
    else:
        with tracking_recorder.run_context(
            source_system=ProjectEnrichmentLoader.SOURCE_SYSTEM,
            flow_name="Enrich SigPesq Projects",
        ):
            stats = _run()

    logger.info(f"Enrichment finished: {stats}")
    return stats


if __name__ == "__main__":
    enrich_projects_flow()

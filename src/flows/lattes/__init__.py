from src.flows.lattes.advisorships import ingest_lattes_advisorships_flow
from src.flows.lattes.complete import lattes_complete_flow
from src.flows.lattes.download import download_lattes_flow
from src.flows.lattes.projects import ingest_lattes_projects_flow

__all__ = [
    "download_lattes_flow",
    "ingest_lattes_advisorships_flow",
    "ingest_lattes_projects_flow",
    "lattes_complete_flow",
]

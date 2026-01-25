import asyncio

from src.flows.export_canonical_data import export_canonical_data_flow
from src.flows.export_knowledge_areas_mart import export_knowledge_areas_mart_flow
from src.flows.export_initiatives_analytics_mart import (
    export_initiatives_analytics_mart_flow,
)
from src.flows.sync_cnpq_groups import sync_cnpq_groups_flow


from src.flows.ingest_sigpesq_groups import ingest_research_groups_flow
from src.flows.ingest_sigpesq_projects import ingest_projects_flow

def run_pipeline():
    campus = "Serra"
    
    print(f"\n>>> 1. Running SigPesq Research Groups Ingestion")
    ingest_research_groups_flow()

    print(f"\n>>> 2. Running CNPq Sync for campus: {campus}")
    sync_cnpq_groups_flow(campus_name=campus)

    print(f"\n>>> 3. Running SigPesq Projects Ingestion")
    ingest_projects_flow()

    print(f"\n>>> 4. Running Canonical Export for campus: {campus}")
    export_canonical_data_flow(campus=campus)

    print(f"\n>>> 5. Running Knowledge Areas Mart for campus: {campus}")
    export_knowledge_areas_mart_flow(campus=campus)

    print(f"\n>>> 6. Running Initiative Analytics Mart (Global)")
    export_initiatives_analytics_mart_flow()

    print("\n>>> Pipeline execution completed.")


if __name__ == "__main__":
    run_pipeline()

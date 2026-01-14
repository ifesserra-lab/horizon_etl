import asyncio

from src.flows.export_canonical_data import export_canonical_data_flow
from src.flows.export_knowledge_areas_mart import export_knowledge_areas_mart_flow
from src.flows.sync_cnpq_groups import sync_cnpq_groups_flow


def run_pipeline():
    campus = "Serra"
    print(f"\n>>> 1. Running CNPq Sync for campus: {campus}")
    sync_cnpq_groups_flow(campus_name=campus)

    print(f"\n>>> 2. Running Canonical Export for campus: {campus}")
    export_canonical_data_flow(campus=campus)

    print(f"\n>>> 3. Running Knowledge Areas Mart for campus: {campus}")
    export_knowledge_areas_mart_flow(campus=campus)

    print("\n>>> Pipeline execution completed.")


if __name__ == "__main__":
    run_pipeline()

# Horizon ETL

**Horizon ETL** is a modern, scalable data pipeline built with **Python**, **Prefect**, and **Supabase**.
It follows **Hexagonal Architecture** principles combined with a **Source/Transform/Sink** component model to ensure robustness, testability, and easy extensibility.

## 🏗 Architecture

The project is structured to separate concerns strictly:

```text
src/
├── core/                  # The "Hexagon" (Pure Business Logic)
│   ├── ports/             # Interfaces (Contracts for Sources/Sinks)
│   ├── domain/            # Data Schemas (Pydantic Models)
│   └── logic/             # Pure Transformations (Mappers/Cleaners)
│
├── adapters/              # The "Infrastructure" (Real World)
│   ├── sources/           # Implementations (FapesScraper, CnpqCrawler)
│   └── sinks/             # Implementations (SupabaseRepo, JsonSink, S3Bucket)
│
└── flows/                 # The Orchestration (Prefect)
    └── sync_cnpq_groups.py # Orchestrates CNPq Sync
    └── export_canonical.py # Orchestrates Data Export
```

## 🚀 Key Features

*   **Idempotency:** Proper handling of natural keys and Upserts to prevent data duplication.
*   **Observability:** Integrated logging and Data Lineage via Prefect Artifacts.
*   **Auditability:** Raw data storage for debugging and historical replay.
*   **Extensibility:** Plug-and-play architecture using Ports & Adapters.
*   **CNPq Synchronization:** 
    *   Automated extraction of Research Groups from Lattes/CNPq.
    *   **Research Lines:** Maps CNPq 'linhas_de_pesquisa' to 'Knowledge Areas'.
    *   **Self-Healing:** Robust researcher recovery and association.
*   **Canonical Data Export:** Generates standardized JSON dumps for Organizations, Campuses, Knowledge Areas, Researchers, and Research Groups.

## 🛠 Stack

*   **Orchestrator:** [Prefect 3](https://www.prefect.io/)
*   **Database:** [Supabase](https://supabase.com/) (PostgreSQL)
*   **Language:** Python 3.10+
*   **Validation:** Pydantic

## 📦 Getting Started

### 1. Installation

```bash
git clone https://github.com/ifesserra-lab/horizon_etl.git
cd horizon_etl
pip install -e .
```

### 2. Running Flows

**Sync CNPq Research Groups:**
```bash
# Sync specific campus (e.g., Serra)
python app.py cnpq_sync Serra
```

**Export Canonical Data:**
```bash
# Exports to data/exports/
python app.py export_canonical

# Export with Campus Filter
python app.py export_canonical data/exports "Serra"
```

**Generate Knowledge Area Mart:**
```bash
# Generate Mart JSON
python app.py ka_mart

# Generate Mart filtered by Campus
python app.py ka_mart data/exports/mart.json "Serra"
```

## 📜 Version History

*   **v0.5.0**: CNPq Sync Enhanced (Research Lines & Knowledge Areas), Canonical Exports, Fix for Researcher Persistence.
*   **v0.4.0**: Base CNPq Synchronization.
*   **v0.3.0**: SigPesq Enhancements & Granular Strategy Pattern.
*   **v0.2.0**: Research Group Ingestion & Local Infrastructure.

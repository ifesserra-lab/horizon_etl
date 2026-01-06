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
│   ├── sources/           # Implementations (FapesScraper, APIClient)
│   └── sinks/             # Implementations (SupabaseRepo, S3Bucket)
│
└── flows/                 # The Orchestration (Prefect)
    └── ingest_data.py     # Wires Adapters to Logic
```

## 🚀 Key Features

*   **Idempotency:** Proper handling of natural keys and Upserts to prevent data duplication.
*   **Observability:** Integrated logging and Data Lineage via Prefect Artifacts.
*   **Auditability:** Raw data storage for debugging and historical replay.
*   **Extensibility:** Plug-and-play architecture using Ports & Adapters.

## 🛠 Stack

*   **Orchestrator:** [Prefect 3](https://www.prefect.io/)
*   **Database:** [Supabase](https://supabase.com/) (PostgreSQL)
*   **Language:** Python 3.10+
*   **Validation:** Pydantic

## 📦 Getting Started

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/ifesserra-lab/horizon_etl.git
    cd horizon_etl
    ```

2.  **Install dependencies:**
    ```bash
    pip install -e .
    ```

3.  **Run a Flow:**
    ```bash
    python flows/ingest_fapes.py
    ```

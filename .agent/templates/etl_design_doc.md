# ETL Design Document: [Feature/Flow Name]

## 1. Overview
Brief description of the data being ingested/exported and its purpose.

## 2. Ingestion Path
- **Source**: [e.g., Lattes JSON]
- **Extractor**: [Class/Adapter Name]
- **Loading Strategy**: [Batch/Incremental]

## 3. Data Mapping Matrix
| Source Key | Logic | Target Attribute |
|------------|-------|------------------|
| | | |

## 4. Entity Relationship (Domain Impact)
Describe how this data links to:
- Researchers
- Initiatives
- Organizations

## 5. Idempotency & Conflict Resolution
- **Unique Constraint**: [e.g., name + start_date]
- **Policy**: [e.g., UPSERT - Overwrite on match]

## 6. Observability
- **Logs**: Key info/error log patterns.
- **Metrics**: Success/Failure counts.

## 7. Verification Steps
1. Run flow: `python app.py ...`
2. Query: `SELECT ...`
3. Inspect: `data/exports/...`

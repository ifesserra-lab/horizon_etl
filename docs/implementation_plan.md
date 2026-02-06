# Enforce AdvisorshipType in Ingestion

## Goal Description
Ensure that every Advisorship created during Lattes ingestion has its `type` field correctly populated with the appropriate `AdvisorshipType` enum value. Currently, only the generic `initiative_type_id` is set, leaving the specific `type` column null.

## User Review Required
None. This is a logic refinement to ensure data completeness.

## Proposed Changes

### [Flows]
#### [MODIFY] [ingest_lattes_advisorships.py](file:///home/paulossjunior/projects/horizon_project/horizon_etl/src/flows/ingest_lattes_advisorships.py)
- **Import**: `AdvisorshipType` from `research_domain.domain.entities.advisorship`.
- **Mapping**: Create a dictionary mapping the strings returned by `LattesParser` (e.g., "Master's Thesis") to `AdvisorshipType` (e.g., `AdvisorshipType.MASTER_THESIS`).
- **Logic**: 
    - Inside the loop, map `item["type"]` (which is the canonical string) to the Enum.
    - Pass this value to the `Advisorship` constructor as `type=mapped_type`.

## Verification Plan

### Automated Tests
- Create a temporary test script `tests/verify_advisorship_type.py`:
  - It will query the database for the most recent Advisorships.
  - Assert that `type` is NOT NULL and is a valid `AdvisorshipType`.
- Run the ingestion flow for a sample file.

### Manual Verification
- Check the logs to ensure no mapping errors occur.
- Inspect the database or object representation to confirm persistence.

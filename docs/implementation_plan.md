# Expanding Fellowship Data in Export

The objective is to include full fellowship details (ID, Name, Description, Value) in the `advisorships_canonical.json` export for each advisorship.

## Proposed Changes

### [Core Logic Layer]

#### [MODIFY] [canonical_exporter.py](file:///home/paulossjunior/projects/horizon_project/horizon_etl/src/core/logic/canonical_exporter.py)
- In `export_advisorships`:
    1. Update the main SQL query to `LEFT JOIN fellowships f ON a.fellowship_id = f.id`.
    2. Fetch fields: `f.name as fellowship_name`, `f.description as fellowship_description`, `f.value as fellowship_value`.
    3. Replace `fellowship_id` in `adv_data` with a `fellowship` object containing the fetched details.

## Verification Plan

### Manual Verification
- Run `export_canonical_data.py`.
- View `data/exports/advisorships_canonical.json` and verify the `fellowship` structure:
```json
{
  "id": 123,
  "name": "Advisorship Name",
  "fellowship": {
    "id": 3,
    "name": "PIBITI",
    "description": "...",
    "value": 700.0
  },
  ...
}
```

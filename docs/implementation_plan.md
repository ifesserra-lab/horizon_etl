# Advisorship Analytics Mart Proposal

The objective is to transform the hierarchical `advisorships_canonical.json` into a focused analytical dataset (`advisorship_analytics.json`) for dashboards and reports.

## Proposed Indicators

### 1. Project Metrics (per Project)
- `total_students`: Count of advisorships.
- `active_students`: Count of students where status is "Active".
- `monthly_investment`: Sum of `fellowship.value`.
- `main_funding_program`: Most frequent fellowship name in the project.
- `team_size`: Total members in the `team` list.

### 2. Global Aggregates
- `total_active_advisorships`: Sum of all active students across all projects.
- `investment_distribution`: Breakdown of total value per program (e.g., "PIBITI: 5600.00").
- `participation_ratio`: Average students per research project.
- `volunteer_percentage`: (Students with 0.0 value / Total students) * 100.

### 3. Rankings (Top 10)
- `top_supervisors_by_count`: Name and student count.
- `top_projects_by_investment`: Project name and total monthly value.

## Proposed Changes

### [Core Logic Layer]

#### [MODIFY] [canonical_exporter.py](file:///home/paulossjunior/projects/horizon_project/horizon_etl/src/core/logic/canonical_exporter.py)
- Add `generate_advisorship_mart(self, input_path, output_path)`:
    - Load the canonical JSON.
    - Iterate through projects and advisorships to calculate the above metrics.
    - Structure the final JSON into `{"projects": [...], "global_stats": {...}, "rankings": {...}}`.
    - Use `self.sink.export`.

## Verification Plan

### Automated Tests
- Create a test case that loads a sample hierarchical JSON and verifies the calculated totals and rankings.

### Manual Verification
- Run the mart generation.
- Check `data/exports/advisorship_analytics.json` for logical consistency (e.g., global totals match the sum of project totals).

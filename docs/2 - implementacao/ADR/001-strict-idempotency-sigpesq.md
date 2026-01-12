# ADR 001: Strict Idempotency (Do Nothing if Exists) for SigPesq Ingestion

* Status: Accepted
* Deciders: Antigravity, Paulo
* Date: 2026-01-12

Technical Story: Ingestion of SigPesq data was failing with `IntegrityError` due to duplicate `identification_id` (email) for researchers. Re-running the pipeline on existing data was attempting to re-create entities instead of ignoring them.

## Context and Problem Statement

The SigPesq data source (Excel) provides a flattened view of research groups and their leaders. When the pipeline runs multiple times, or when a researcher belongs to multiple groups, the current logic attempts to ensure their existence. 

Standard `UPSERT` behavior (Update if exists) might overwrite manually curated data in the database. Furthermore, the current implementation was failing to correctly identify existing researchers when only looking up by name, leading to `IntegrityError` on the unique email field.

## Decision Drivers

* Prevent data duplication and database integrity errors.
* Protect manually refined or enriched data in the `persons` and `researchers` tables from being overwritten by raw SigPesq data.
* Improve pipeline performance by skipping unnecessary database operations.

## Considered Options

* **Option 1: Standard UPSERT** - Update all fields if the entity exists.
* **Option 2: Strict Idempotency (Do Nothing)** - If the entity exists (based on a unique key like email or name), skip the creation and update entirely.
* **Option 3: Partial Update** - Only update specific empty fields.

## Decision Outcome

Chosen option: **Option 2: Strict Idempotency (Do Nothing)**, because it ensures that existing data (which may have been enriched by other flows like CNPq or manual edits) remains unchanged by the less-reliable SigPesq source.

### Consequences

* Good: Resolves `IntegrityError` by correctly identifying existing records.
* Good: Prevents loss of enriched data.
* Good: Faster execution for subsequent runs.
* Bad: New changes in SigPesq (e.g., a researcher changing their name in the source system) will not be reflected automatically. This is acceptable as Lattes/CNPq are considered more authoritative.

## Pros and Cons of the Options

### Option 1: Standard UPSERT

* Good: Always keeps data in sync with SigPesq.
* Bad: Risk of overwriting data from more authoritative sources.
* Bad: More complex implementation for many-to-many relationships (e.g., adding a leader that is already associated).

### Option 2: Strict Idempotency (Do Nothing)

* Good: Safest for data integrity.
* Good: Simple to implement in strategies.
* Bad: Requires manual intervention or a separate sync flow to update existing records if SigPesq data changes significantly.

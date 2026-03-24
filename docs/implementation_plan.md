# Implementation Plan - Runtime and Packaging Consistency

## Goal Description
Align the repository packaging and runtime manifests so installation, editable development, and documented commands rely on a consistent dependency set.

## Scope
- Reconcile `pyproject.toml` and `requirements.txt`.
- Add or correct build metadata needed for editable installation.
- Ensure documented installation steps match the current repository reality.
- Preserve current application behavior without refactoring ETL logic.

## Non-Goals
- Change ETL business rules.
- Reorganize application modules.
- Introduce dependency upgrades beyond the versions already implied by the repository state.

## Current Problems Identified
1. `pyproject.toml` and `requirements.txt` define different dependency sets and different Prefect versions.
2. Several runtime dependencies used by the code are missing from `pyproject.toml`.
3. `pyproject.toml` does not declare a build backend.
4. The current setuptools package configuration is not robust for editable installs of `src` subpackages.
5. The documented setup flow did not mention a recovery path when a local virtual environment is missing `pip`.

## Proposed Changes
1. Make `pyproject.toml` the authoritative structured manifest for build metadata and dependency declaration.
2. Mirror the same runtime dependencies in `requirements.txt` for environment bootstrap convenience.
3. Add missing dependencies actually referenced by code, including logging, fuzzy matching, Excel parsing, CNPq sync support, and scriptLattes integration.
4. Add a setuptools build backend and package discovery configuration.
5. Update the README installation notes to match the manifest changes.

## Verification Plan
- Compare runtime imports in `src/`, `scripts/`, `db/`, and `app.py` against declared dependencies.
- Review `git diff` for all manifest and documentation changes.
- Attempt lightweight environment validation where possible in the current workspace.

## Risks and Controls
- Risk: Declaring dependencies not available in the current local environment may still leave installation blocked.
  - Control: Keep changes limited to declared requirements and document the local environment limitation explicitly.
- Risk: Packaging changes could affect downstream tooling assumptions.
  - Control: Avoid module renames or source layout changes in this increment.

## Deliverables
- Consistent dependency manifests.
- Corrected build metadata for editable installation.
- Updated setup documentation.

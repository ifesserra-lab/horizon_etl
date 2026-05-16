# Feature: Containerized Application Deployment

**Branch**: feat/002-docker-compose-app
**Created**: 2026-05-16
**Status**: Draft

## User Scenarios & Testing

### [P1] Developer One-Command Startup

As a developer, I want to start the entire Horizon ETL system with a single command so I can begin running pipelines without manually configuring services or installing dependencies.

**Priority rationale**: Unlocks all other usage; without this, the system is inaccessible to new contributors.

**Independent test**: System is fully operational (pipeline runs, data is stored) after running one command from a clean machine with only credentials configured.

**Acceptance scenarios**:

Given a machine with credentials configured in a local environment file
When the developer runs the single startup command
Then all services start in dependency order
And the workflow orchestration interface becomes accessible
And the ETL pipeline can be triggered and completes successfully

Given a developer who has never used the system before
When they follow the getting-started instructions
Then the system is running within 5 minutes

**Edge cases**:
- Required credentials are missing → system fails immediately with a descriptive error listing the missing values
- One service is already running → remaining services start without conflict
- Startup interrupted mid-way → partial state is cleanly recoverable by re-running the startup command

---

### [P2] Data Persistence Across Restarts

As a developer, I want data ingested in previous runs to survive when I stop and restart the system so I do not lose work or have to re-ingest large datasets.

**Priority rationale**: Without persistence, every restart forces a full re-ingestion which can take hours.

**Independent test**: Ingest data, stop all services, restart, verify previously ingested data is present and exports match pre-restart state.

**Acceptance scenarios**:

Given the system has completed a pipeline run with data stored
When the developer stops and restarts all services
Then all previously ingested records are accessible
And exports regenerated after restart are identical to pre-restart exports

**Edge cases**:
- System crashes during write → data from completed pipeline steps is preserved; in-progress step restarts cleanly
- Storage volume is full → failure is reported before data corruption occurs

---

### [P3] External Service Access from Containers

As a developer, I want the containerized application to access external portals (SigPesq, Lattes, CNPq) so that ingestion pipelines work identically inside and outside containers.

**Priority rationale**: Core ingestion flows depend on external scraping; if networking is broken in container, the system is unusable.

**Independent test**: Run each source-specific ingestion flow from inside the container and verify data is ingested successfully.

**Acceptance scenarios**:

Given the system is running in containers
When a developer triggers the SigPesq, Lattes, or CNPq ingestion flow
Then the flow completes with the same result as a local (non-containerized) run

**Edge cases**:
- External portal is unreachable → error is reported with same message as non-containerized run; no container-specific failure

## Functional Requirements

- **FR-001** [P1]: The system provides a single startup command that brings all required services online in the correct dependency order.
- **FR-002** [P1]: The startup command fails with a descriptive error if required credentials are missing before any service starts.
- **FR-003** [P1]: A sample credentials template file is available so developers know which values to configure.
- **FR-004** [P2]: All pipeline-produced data (ingested records, exported files) persists in named storage volumes that survive service restarts.
- **FR-005** [P2]: A single command stops all running services without data loss.
- **FR-006** [P3]: All pipeline flows that access external portals (SigPesq, Lattes, CNPq) work identically when triggered from inside the containerized environment.
- **FR-007** [P3]: Pipeline flows can be triggered from within the running system using the same commands as in non-containerized operation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All services reach a healthy, ready state within 2 minutes of running the startup command on a machine where service images are already downloaded.
- **SC-002**: A developer following the getting-started instructions has the full system running within 10 minutes on first setup (including image download time).
- **SC-003**: 100% of pipeline flows produce identical output (same record counts, same export file structure) whether run inside or outside containers.
- **SC-004**: Data from at least 10 previous pipeline runs survives a full system restart with zero record loss.
- **SC-005**: Zero manual steps are required between "credentials configured" and "pipeline ready to run".

## Assumptions

- Target users are developers running the system locally for development and data ingestion; production deployment is out of scope.
- Credentials (SigPesq username/password, optional Telegram tokens) are provided via a local environment file that is never committed to version control.
- The machine running the system has internet access to reach external portals (SigPesq, Lattes, CNPq).
- Users have the container runtime installed before following setup instructions.
- The existing Prefect infrastructure (database + server) is incorporated into the unified startup rather than replaced.
- SQLite is the default local database; PostgreSQL (Supabase) integration is out of scope for this feature.

## Out of Scope

- Production/cloud deployment configuration
- CI/CD pipeline integration
- Multi-user or shared-server deployment
- Automated data backup or disaster recovery
- PostgreSQL as the application database (local SQLite only)

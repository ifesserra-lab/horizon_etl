# Research: Containerized Application Deployment

**Feature**: 002-docker-compose-app
**Date**: 2026-05-16

---

## Decision 1: Base Container Image

**Decision**: `python:3.12-slim` (Debian Bookworm) as the ETL app base image.

**Rationale**: Matches the project's Python 3.12 requirement, has `apt` for Chromium system packages, and is the smallest Debian-based image. Multi-stage build reduces final image size by ~200MB.

**Alternatives considered**:
- `mcr.microsoft.com/playwright/python:v1.x.x-jammy` — pre-installs Playwright browsers but is Ubuntu-based and larger (~1.5GB). Overkill since we also need Selenium/ChromeDriver.
- `python:3.12-alpine` — smallest base, but Chromium system dependency resolution is fragile on Alpine. Rejected due to known compatibility issues with Playwright and Selenium.

---

## Decision 2: Browser Runtime (Playwright + Selenium in One Container)

**Decision**: Single container with `chromium-browser` + `chromium-chromedriver` installed via `apt`, plus `playwright install --with-deps chromium`.

**Rationale**: Both SigPesq (Playwright) and Lattes (Selenium/scriptLattes) use Chromium. Combining in one container avoids volume-sharing complexity, reduces startup overhead, and uses the same shared system libraries. Debian's `chromium-chromedriver` package is auto-versioned to match `chromium-browser` — no version mismatch risk.

**Alternatives considered**:
- Two separate containers (one for Playwright, one for Selenium) — adds orchestration complexity, requires shared data volumes for a sequential pipeline. Rejected.
- `selenium/standalone-chrome` base image — Ubuntu-based, not Python, requires sidecar pattern. Rejected.
- `webdriver-manager` Python package — downloads ChromeDriver at runtime, requires internet access on container startup. Rejected in favor of system package.

---

## Decision 3: ETL Container Lifecycle Pattern

**Decision**: `docker compose run --rm app python app.py [flow] [args]` — ephemeral one-shot container per pipeline run.

**Rationale**: `app.py` is a CLI dispatcher, not a server. One-shot execution is idempotent, produces clean container state per run, and aligns with the existing `make pipeline` pattern. No persistent daemon needed.

**Alternatives considered**:
- Long-running container with `tail -f /dev/null` + `docker exec` — container must be started first, wastes resources when idle, state accumulates across runs. Rejected.
- Prefect worker sidecar — correct for distributed deployments, but adds significant complexity for a local single-machine setup. Deferred to a future feature.
- `docker compose up app` with a default CMD — requires a sensible default command and complicates the "run specific flows" use case. Rejected.

---

## Decision 4: Data Volume Strategy

**Decision**: Bind mounts for all application data directories; named volume only for the Prefect PostgreSQL database.

**Rationale**: Bind mounts (`./db:/app/db`, `./data/exports:/app/data/exports`, etc.) allow direct inspection of SQLite DB, export JSONs, and log files from the host machine — critical for development workflows. Named volumes are used only for Prefect's internal state (PostgreSQL), which developers do not need to inspect directly.

**Alternatives considered**:
- All named volumes — developer cannot inspect SQLite or exports without `docker cp`. Anti-pattern for active development. Rejected.
- All bind mounts including Prefect DB — unnecessary, Prefect DB does not need host access. Rejected.

**Mapped directories**:
| Host path | Container path | Purpose |
|-----------|---------------|---------|
| `./db` | `/app/db` | SQLite database |
| `./data/exports` | `/app/data/exports` | JSON exports |
| `./data/lattes_json` | `/app/data/lattes_json` | Lattes CV JSONs |
| `./cache` | `/app/cache` | scriptLattes browser cache |
| `./logs` | `/app/logs` | Pipeline logs |

---

## Decision 5: Prefect API URL (Internal Network)

**Decision**: App container sets `PREFECT_API_URL=http://server:4200/api` via compose `environment:` override.

**Rationale**: Docker Compose creates an internal network where services reference each other by service name. `localhost` inside the container refers to the app container itself, not the Prefect server. The existing `PREFECT_UI_API_URL=http://127.0.0.1:4200/api` in the server service is correct — it configures the browser UI URL (resolved by the developer's host browser, not the container).

**Alternatives considered**:
- `host.docker.internal` — macOS-specific. Rejected for portability.
- Sharing host network (`network_mode: host`) — eliminates container network isolation. Rejected.

---

## Decision 6: Prefect Server Health Check

**Decision**: Add `healthcheck` to the `server` service (HTTP GET to `/api/health`); app service uses `condition: service_healthy`.

**Rationale**: Without a health check, `depends_on` only waits for the container to start — not for the Prefect API to be ready. The server takes ~5–10 seconds after process start before accepting connections. A health check eliminates race conditions.

**Alternatives considered**:
- `sleep` in app entrypoint — brittle, environment-dependent. Rejected.
- `condition: service_started` (current) — insufficient; API may not be ready. Replaced.

---

## Decision 7: Credentials Injection

**Decision**: `env_file: .env` in the app service, with `environment:` block overriding `PREFECT_API_URL` to the internal network URL.

**Rationale**: `env_file:` loads the developer's `.env` cleanly without duplicating variable definitions in the compose file. The `PREFECT_API_URL` override is required because the `.env` file sets `http://127.0.0.1:4200/api` (correct for local runs) but inside Docker the URL must use the service name.

---

## Decision 8: Makefile Integration

**Decision**: Add `docker-*` prefixed targets alongside existing local targets. No changes to existing targets.

**Rationale**: Keeps local and Docker workflows independent. Existing `make pipeline`, `make ingest-sigpesq`, etc. continue to work unchanged. Docker variants (`make docker-pipeline`, `make docker-ingest-sigpesq`) invoke `docker compose run --rm app python app.py [args]`.

---

## Decision 9: LGPD Compliance in Container

**Decision**: No additional LGPD changes required; existing mechanism applies automatically.

**Rationale**: The LGPD session hook (`pii_session_hook.py`) is installed at `app.py` startup, which runs identically inside the container. All flows go through the same code path. Export anonymization is enforced by the same middleware. Container boundary does not affect compliance.

---

## Decision 10: `.env` Validation on Container Startup

**Decision**: Add an `.env` presence check in the Makefile `docker-*` targets; the app itself already fails loudly when `SIGPESQ_USERNAME` is missing.

**Rationale**: FR-002 requires the system to fail with a descriptive error if credentials are missing. The existing `SigPesqAdapter._validate_environment()` raises `EnvironmentError` with a message listing missing variables. The Makefile check adds an early exit before Docker even starts, improving UX.

# Horizon ETL automation

SHELL := /bin/sh
.DEFAULT_GOAL := help

PREFECT_HOST ?= 127.0.0.1
PREFECT_PORT ?= 4200
PREFECT_API_URL ?= http://$(PREFECT_HOST):$(PREFECT_PORT)/api
PREFECT_ENV := PREFECT_API_URL=$(PREFECT_API_URL) PREFECT_CLIENT_SERVER_VERSION_CHECK_ENABLED=false

PYTHON_BIN ?= .venv/bin/python
PYTHON_ENV := $(PREFECT_ENV) PYTHONPATH=.
PYTHON := $(PYTHON_ENV) $(PYTHON_BIN)
FLOW_ENV := HORIZON_QUIET_PREFECT=1 PREFECT_LOGGING_TO_API_ENABLED=false
FLOW_PYTHON := $(FLOW_ENV) $(PYTHON)

CAMPUS ?= Serra
WEEKLY_CAMPUS ?=
OUTPUT_DIR ?= data/exports

DOCKER_BIN ?= $(shell if command -v docker >/dev/null 2>&1; then echo docker; elif command -v flatpak-spawn >/dev/null 2>&1 && flatpak-spawn --host sh -lc 'command -v docker >/dev/null 2>&1'; then echo "flatpak-spawn --host docker"; else echo docker; fi)
DOCKER_COMPOSE_FILE ?= docker-compose.yml
DOCKER_COMPOSE := $(DOCKER_BIN) compose -f $(DOCKER_COMPOSE_FILE)
PREFECT_SERVER_SERVICE ?= server
PREFECT_DB_SERVICE ?= database

.PHONY: help setup logs-dir \
	db-clean db-init db-reset clean-db init-db reset-db \
	prefect-server prefect-stop prefect-status \
	pipeline pipeline-serra pipeline-unified pipeline-log weekly-flows full-refresh full-refresh-serra \
	ingest-sigpesq sigpesq ingest-groups ingest-projects ingest-advisorships \
	ingest-lattes-download ingest-lattes-projects ingest-lattes-advisorships ingest-lattes-full \
	sync-cnpq sync-cnpq-serra \
	export export-canonical export-serra export-knowledge-areas-mart export-initiatives-analytics-mart export-people-graph export-advisorships export-advisorship-analytics export-analytics \
	test test-advisorships test-coverage lint format format-check ci-check dev-cycle \
	verify-status verify-exports audit-duplicates harden-db consolidate-duplicates consolidate-duplicates-dry \
	etl-report etl-report-md tracking-audit-report tracking-query status clean all

help: ## Show available commands
	@echo "Horizon ETL commands"
	@echo "===================="
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-34s %s\n", $$1, $$2}'

setup: ## Create venv, install dependencies, and create local folders
	@python3 -m venv .venv
	@$(PYTHON_BIN) -m pip install --upgrade pip
	@$(PYTHON_BIN) -m pip install -r requirements.txt
	@mkdir -p logs data/exports

logs-dir: ## Create the logs directory
	@mkdir -p logs

db-clean: ## Delete the local SQLite database
	@rm -f db/horizon.db

db-init: ## Initialize database schema and base data
	@$(PYTHON) db/create_db.py

db-reset: db-clean db-init ## Recreate the local database from scratch

clean-db: db-clean ## Alias for db-clean

init-db: db-init ## Alias for db-init

reset-db: db-reset ## Alias for db-reset

prefect-server: logs-dir ## Start local Prefect server with Docker Compose
	@if $(DOCKER_COMPOSE) ps --services --status running | grep -qx "$(PREFECT_SERVER_SERVICE)"; then \
		echo "Prefect server already running at $(PREFECT_API_URL)"; \
	else \
		echo "Starting Prefect server at $(PREFECT_API_URL)"; \
		$(DOCKER_COMPOSE) up -d $(PREFECT_DB_SERVICE) $(PREFECT_SERVER_SERVICE); \
		for i in `seq 1 30`; do \
			if curl -fsS "$(PREFECT_API_URL)/health" >/dev/null 2>&1; then \
				echo "Prefect server is ready at $(PREFECT_API_URL)"; \
				exit 0; \
			fi; \
			sleep 1; \
		done; \
		echo "Prefect server did not become ready. Recent logs:"; \
		$(DOCKER_COMPOSE) logs --tail=50 $(PREFECT_SERVER_SERVICE); \
		exit 1; \
	fi

prefect-stop: ## Stop local Prefect server containers
	@if $(DOCKER_COMPOSE) ps --services --status running | grep -Eq "^($(PREFECT_SERVER_SERVICE)|$(PREFECT_DB_SERVICE))$$"; then \
		$(DOCKER_COMPOSE) stop $(PREFECT_SERVER_SERVICE) $(PREFECT_DB_SERVICE); \
	else \
		echo "No Prefect server containers are running"; \
	fi

prefect-status: ## Show local Prefect server status
	@if $(DOCKER_COMPOSE) ps --services --status running | grep -qx "$(PREFECT_SERVER_SERVICE)"; then \
		echo "Prefect server running at $(PREFECT_API_URL)"; \
		$(DOCKER_COMPOSE) ps $(PREFECT_DB_SERVICE) $(PREFECT_SERVER_SERVICE); \
	else \
		echo "Prefect server is not running"; \
	fi

pipeline: pipeline-unified ## Run the unified pipeline for CAMPUS

pipeline-serra: prefect-server ## Run the unified pipeline for Serra
	@$(FLOW_PYTHON) app.py full_pipeline Serra "$(OUTPUT_DIR)"

pipeline-unified: prefect-server ## Run the unified pipeline for CAMPUS
	@$(FLOW_PYTHON) app.py full_pipeline "$(CAMPUS)" "$(OUTPUT_DIR)"

pipeline-log: prefect-server logs-dir ## Run the unified pipeline and tee output to logs/
	@$(FLOW_PYTHON) app.py full_pipeline "$(CAMPUS)" "$(OUTPUT_DIR)" 2>&1 | tee logs/pipeline_$(CAMPUS)_$$(date +%Y%m%d_%H%M%S).log

weekly-flows: db-reset prefect-server ## Reset DB and run weekly source flows plus exports
	@$(FLOW_PYTHON) app.py weekly "$(WEEKLY_CAMPUS)" "$(OUTPUT_DIR)"

full-refresh: db-reset prefect-server ## Reset DB and run the unified pipeline without campus filter
	@$(FLOW_PYTHON) -c "from src.prefect_runtime import bootstrap_local_prefect; bootstrap_local_prefect(); from src.flows.pipelines.unified import full_ingestion_pipeline; full_ingestion_pipeline(campus_name=None, output_dir='$(OUTPUT_DIR)')"

full-refresh-serra: db-reset pipeline-serra ## Reset DB and run the Serra pipeline

ingest-sigpesq: prefect-server ## Ingest all SigPesq reports with one login
	@$(FLOW_PYTHON) app.py sigpesq

sigpesq: ingest-sigpesq ## Alias for ingest-sigpesq

ingest-groups: prefect-server ## Ingest SigPesq research groups only
	@$(FLOW_PYTHON) -m src.flows.sigpesq.groups

ingest-projects: prefect-server ## Ingest SigPesq projects only
	@$(FLOW_PYTHON) -m src.flows.sigpesq.projects

ingest-advisorships: prefect-server ## Ingest SigPesq advisorships only
	@$(FLOW_PYTHON) -m src.flows.sigpesq.advisorships

ingest-lattes-download: prefect-server ## Download Lattes curricula only
	@$(FLOW_PYTHON) -m src.flows.lattes.download

ingest-lattes-projects: prefect-server ## Ingest Lattes projects/articles/education only
	@$(FLOW_PYTHON) -m src.flows.lattes.projects

ingest-lattes-advisorships: prefect-server ## Ingest Lattes advisorships only
	@$(FLOW_PYTHON) -m src.flows.lattes.advisorships

ingest-lattes-full: prefect-server ## Run the complete Lattes ingestion flow
	@$(FLOW_PYTHON) -m src.flows.lattes.complete

sync-cnpq: prefect-server ## Sync CNPq data for CAMPUS
	@$(FLOW_PYTHON) app.py cnpq_sync "$(CAMPUS)"

sync-cnpq-serra: prefect-server ## Sync CNPq data for Serra
	@$(FLOW_PYTHON) app.py cnpq_sync Serra

export: export-canonical ## Alias for export-canonical

export-canonical: prefect-server ## Export canonical data for CAMPUS
	@$(FLOW_PYTHON) app.py export_canonical "$(OUTPUT_DIR)" "$(CAMPUS)"

export-serra: prefect-server ## Export canonical data for Serra
	@$(FLOW_PYTHON) app.py export_canonical "$(OUTPUT_DIR)" Serra

export-knowledge-areas-mart: prefect-server ## Export the knowledge areas mart
	@$(FLOW_PYTHON) app.py ka_mart "$(OUTPUT_DIR)/knowledge_areas_mart.json" "$(CAMPUS)"

export-initiatives-analytics-mart: prefect-server ## Export the initiatives analytics mart
	@$(FLOW_PYTHON) app.py analytics_mart "$(OUTPUT_DIR)/initiatives_analytics_mart.json"

export-people-graph: prefect-server ## Export the people relationship graph
	@$(FLOW_PYTHON) app.py people_graph "$(OUTPUT_DIR)"

export-advisorships: ## Export advisorships canonical data only
	@$(PYTHON) -c "from src.core.logic.canonical_exporter import CanonicalDataExporter; from src.adapters.database.postgres_client import PostgresClient; from src.adapters.sinks.json_sink import JsonSink; CanonicalDataExporter(PostgresClient(), JsonSink()).export_advisorships('$(OUTPUT_DIR)/advisorships_canonical.json')"

export-advisorship-analytics: ## Export advisorship analytics only
	@$(PYTHON) -c "from src.core.logic.canonical_exporter import CanonicalDataExporter; from src.adapters.database.postgres_client import PostgresClient; from src.adapters.sinks.json_sink import JsonSink; CanonicalDataExporter(PostgresClient(), JsonSink()).generate_advisorship_mart('$(OUTPUT_DIR)/advisorship_analytics.json')"

export-analytics: export-advisorship-analytics ## Alias for export-advisorship-analytics

test: prefect-server ## Run all tests
	@$(PYTHON) -m pytest -q

test-advisorships: prefect-server ## Run advisorship-related tests
	@$(PYTHON) -m pytest -q -k "advisorship"

test-coverage: prefect-server ## Run tests with coverage
	@$(PYTHON) -m pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run flake8 if available
	@$(PYTHON) -m flake8 src tests

format: ## Format Python code
	@$(PYTHON) -m black src tests
	@$(PYTHON) -m isort src tests

format-check: ## Check Python formatting
	@$(PYTHON) -m black --check src tests
	@$(PYTHON) -m isort --check src tests

ci-check: format-check lint test ## Run CI checks

dev-cycle: format lint test ## Format, lint, and test

verify-status: ## Print sample advisorship statuses from canonical export
	@grep -B 3 '"end_date": "2017' $(OUTPUT_DIR)/advisorships_canonical.json | grep status | head -3
	@grep -B 3 '"end_date": "2026' $(OUTPUT_DIR)/advisorships_canonical.json | grep status | head -3

verify-exports: ## List generated export files
	@ls -lh $(OUTPUT_DIR)/*.json

audit-duplicates: ## Audit duplicate candidates in the current database
	@$(PYTHON) src/scripts/audit_duplicates.py

harden-db: ## Create safe indexes/constraints for duplicate prevention
	@$(PYTHON) src/scripts/harden_db_indices.py

consolidate-duplicates: ## Consolidate duplicate persons, teams, and knowledge areas
	@$(PYTHON) src/scripts/consolidate_duplicates.py --entity all

consolidate-duplicates-dry: ## Preview duplicate consolidations without changing the database
	@$(PYTHON) src/scripts/consolidate_duplicates.py --entity all --dry-run

etl-report: ## Generate ETL extraction vs load reconciliation report
	@$(PYTHON) src/scripts/etl_load_report.py

etl-report-md: ## Generate Markdown from the ETL JSON report
	@$(PYTHON) src/scripts/etl_report_markdown.py

tracking-audit-report: ## Generate tracking-domain audit report
	@$(PYTHON) src/scripts/tracking_audit_report.py

tracking-query: ## Query tracking data with QUERY_ARGS
	@$(PYTHON) src/scripts/tracking_query.py $(QUERY_ARGS)

status: ## Show local database and export status
	@echo "Database:"
	@ls -lh db/horizon.db 2>/dev/null || echo "  not initialized"
	@echo "Exports:"
	@ls -lh $(OUTPUT_DIR)/*.json 2>/dev/null | wc -l | xargs -I {} echo "  {} files exported"
	@echo "Last pipeline log:"
	@ls -lt logs/pipeline_*.log 2>/dev/null | head -1 || echo "  no logs found"

clean: db-clean ## Remove generated caches and local database
	@rm -rf .pytest_cache .coverage htmlcov
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

all: full-refresh verify-status ## Reset, run full refresh, and verify exports

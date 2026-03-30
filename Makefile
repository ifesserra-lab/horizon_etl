# Horizon ETL - Makefile
# Project automation commands following @agile-standards

.PHONY: help clean-db init-db reset-db prefect-server prefect-stop prefect-status pipeline pipeline-unified export test lint format all audit-duplicates harden-db consolidate-duplicates consolidate-duplicates-dry etl-report etl-report-md tracking-audit-report tracking-query

# Python interpreter
PREFECT_HOST := 127.0.0.1
PREFECT_PORT := 4200
PREFECT_API_URL := http://$(PREFECT_HOST):$(PREFECT_PORT)/api
PYTHON := PREFECT_API_URL=$(PREFECT_API_URL) PREFECT_CLIENT_SERVER_VERSION_CHECK_ENABLED=false PYTHONPATH=. .venv/bin/python3
QUIET_PREFECT_ENV := HORIZON_QUIET_PREFECT=1 PREFECT_LOGGING_TO_API_ENABLED=false
FLOW_PYTHON := $(QUIET_PREFECT_ENV) $(PYTHON)
DOCKER_BIN ?= $(shell if command -v docker >/dev/null 2>&1; then echo docker; elif command -v flatpak-spawn >/dev/null 2>&1 && flatpak-spawn --host sh -lc 'command -v docker >/dev/null 2>&1'; then echo "flatpak-spawn --host docker"; else echo docker; fi)
DOCKER_COMPOSE_FILE := docker-compose.yml
DOCKER_COMPOSE := $(DOCKER_BIN) compose -f $(DOCKER_COMPOSE_FILE)
PREFECT_SERVER_SERVICE := server
PREFECT_DB_SERVICE := database

# Campus configuration (default: Serra)
CAMPUS ?= Serra

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Horizon ETL - Available Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Database Management
clean-db: ## Delete the database file
	@echo "🗑️  Cleaning database..."
	@rm -f db/horizon.db
	@echo "✅ Database cleaned"

init-db: ## Initialize database schema and base data
	@echo "🔧 Initializing database..."
	@$(PYTHON) db/create_db.py
	@echo "✅ Database initialized"

reset-db: clean-db init-db ## Clean and reinitialize the database
	@echo "✅ Database reset complete"

# Prefect Server
prefect-server: logs-dir ## Start local Prefect server with Docker Compose
	@if $(DOCKER_COMPOSE) ps --services --status running | grep -qx "$(PREFECT_SERVER_SERVICE)"; then \
		echo "✅ Prefect server already running at $(PREFECT_API_URL)"; \
	else \
		echo "🚀 Starting Prefect server at $(PREFECT_API_URL)..."; \
		$(DOCKER_COMPOSE) up -d $(PREFECT_DB_SERVICE) $(PREFECT_SERVER_SERVICE); \
		for i in `seq 1 30`; do \
			if curl -fsS "$(PREFECT_API_URL)/health" >/dev/null 2>&1; then \
				echo "✅ Prefect server is ready at $(PREFECT_API_URL)"; \
				exit 0; \
			fi; \
			sleep 1; \
		done; \
		echo "❌ Prefect server did not become ready. Recent logs:"; \
		$(DOCKER_COMPOSE) logs --tail=50 $(PREFECT_SERVER_SERVICE); \
		exit 1; \
	fi

prefect-stop: ## Stop local Prefect server containers
	@if $(DOCKER_COMPOSE) ps --services --status running | grep -Eq "^($(PREFECT_SERVER_SERVICE)|$(PREFECT_DB_SERVICE))$$"; then \
		echo "🛑 Stopping Prefect server containers..."; \
		$(DOCKER_COMPOSE) stop $(PREFECT_SERVER_SERVICE) $(PREFECT_DB_SERVICE); \
		echo "✅ Prefect server stopped"; \
	else \
		echo "ℹ️  No Prefect server containers are running"; \
	fi

prefect-status: ## Show Prefect server status
	@if $(DOCKER_COMPOSE) ps --services --status running | grep -qx "$(PREFECT_SERVER_SERVICE)"; then \
		echo "✅ Prefect server running at $(PREFECT_API_URL)"; \
		$(DOCKER_COMPOSE) ps $(PREFECT_DB_SERVICE) $(PREFECT_SERVER_SERVICE); \
	else \
		echo "❌ Prefect server is not running"; \
	fi

# Pipeline Execution
pipeline: prefect-server ## Run the full campus pipeline (default: Serra, use CAMPUS=Name to override)
	@echo "🚀 Running $(CAMPUS) campus pipeline..."
	@$(PYTHON) src/flows/run_serra_pipeline.py

pipeline-serra: prefect-server ## Run the Serra campus pipeline explicitly
	@echo "🚀 Running Serra campus pipeline..."
	@$(PYTHON) src/flows/run_serra_pipeline.py

pipeline-unified: prefect-server ## Run the generic unified pipeline
	@echo "🚀 Running unified pipeline for $(CAMPUS)..."
	@$(FLOW_PYTHON) -c "from src.prefect_runtime import bootstrap_local_prefect; bootstrap_local_prefect(); from src.flows.unified_pipeline import full_ingestion_pipeline; full_ingestion_pipeline(campus_name='$(CAMPUS)', output_dir='data/exports')"
	@echo "📝 Latest ETL report:"
	@echo "   JSON: data/reports/etl_flow_run.json"
	@echo "   MD:   data/reports/etl_flow_run.md"

pipeline-log: prefect-server ## Run pipeline with timestamped log output
	@echo "🚀 Running $(CAMPUS) campus pipeline with logging..."
	@$(PYTHON) src/flows/run_serra_pipeline.py 2>&1 | tee logs/pipeline_$(CAMPUS)_$$(date +%Y%m%d_%H%M%S).log

full-refresh: reset-db prefect-server ## Complete refresh for all campi: clean DB + run unified pipeline without campus filter
	@echo "🚀 Running unified full refresh for all campi..."
	@$(FLOW_PYTHON) -c "from src.prefect_runtime import bootstrap_local_prefect; bootstrap_local_prefect(); from src.flows.unified_pipeline import full_ingestion_pipeline; full_ingestion_pipeline(campus_name=None, output_dir='data/exports')"
	@echo "✅ Full refresh complete for all campi"
	@echo "📝 Latest ETL report:"
	@echo "   JSON: data/reports/etl_flow_run.json"
	@echo "   MD:   data/reports/etl_flow_run.md"

full-refresh-serra: reset-db pipeline-serra ## Complete refresh for Serra campus explicitly
	@echo "✅ Full Serra refresh complete"

# Individual Flow Execution
ingest-groups: ## Ingest SigPesq research groups only
	@echo "📥 Ingesting research groups..."
	@$(PYTHON) src/flows/ingest_sigpesq_groups.py

ingest-projects: ## Ingest SigPesq projects only
	@echo "📥 Ingesting projects..."
	@$(PYTHON) src/flows/ingest_sigpesq_projects.py

ingest-advisorships: ## Ingest SigPesq advisorships only
	@echo "📥 Ingesting advisorships..."
	@$(PYTHON) src/flows/ingest_sigpesq_advisorships.py

sync-cnpq: ## Sync CNPq data for configured campus (default: Serra)
	@echo "🔄 Syncing CNPq data for $(CAMPUS)..."
	@$(PYTHON) -c "from src.flows.sync_cnpq_groups import sync_cnpq_groups_flow; sync_cnpq_groups_flow(campus_name='$(CAMPUS)')"

sync-cnpq-serra: ## Sync CNPq data for Serra campus explicitly
	@echo "🔄 Syncing CNPq data for Serra..."
	@$(PYTHON) -c "from src.flows.sync_cnpq_groups import sync_cnpq_groups_flow; sync_cnpq_groups_flow(campus_name='Serra')"

# Export Operations
export: ## Export all canonical data for configured campus
	@echo "📤 Exporting canonical data for $(CAMPUS)..."
	@$(PYTHON) src/flows/export_canonical_data.py --campus $(CAMPUS)

export-serra: ## Export all canonical data for Serra campus explicitly
	@echo "📤 Exporting canonical data for Serra..."
	@$(PYTHON) src/flows/export_canonical_data.py --campus Serra

export-advisorships: ## Export advisorships canonical data only
	@echo "📤 Exporting advisorships..."
	@$(PYTHON) -c "from src.core.logic.canonical_exporter import CanonicalDataExporter; from src.adapters.database.postgres_client import PostgresClient; from src.adapters.sinks.json_sink import JsonSink; exporter = CanonicalDataExporter(PostgresClient(), JsonSink()); exporter.export_advisorships('data/exports/advisorships_canonical.json')"

export-analytics: ## Export advisorship analytics mart
	@echo "📤 Exporting advisorship analytics..."
	@$(PYTHON) -c "from src.core.logic.canonical_exporter import CanonicalDataExporter; from src.adapters.database.postgres_client import PostgresClient; from src.adapters.sinks.json_sink import JsonSink; exporter = CanonicalDataExporter(PostgresClient(), JsonSink()); exporter.generate_advisorship_mart('data/exports/advisorship_analytics.json')"

# Testing
test: ## Run all tests
	@echo "🧪 Running tests..."
	@$(PYTHON) -m pytest tests/ -v

test-advisorships: ## Run advisorship-related tests only
	@echo "🧪 Running advisorship tests..."
	@$(PYTHON) -m pytest tests/ -v -k "advisorship"

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	@$(PYTHON) -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# Code Quality
lint: ## Run linting checks (flake8)
	@echo "🔍 Running linting checks..."
	@$(PYTHON) -m flake8 src/ tests/ || true

format: ## Format code with black and isort
	@echo "✨ Formatting code..."
	@$(PYTHON) -m black src/ tests/
	@$(PYTHON) -m isort src/ tests/

format-check: ## Check code formatting without modifying
	@echo "🔍 Checking code format..."
	@$(PYTHON) -m black --check src/ tests/
	@$(PYTHON) -m isort --check src/ tests/

# Verification
verify-status: ## Verify advisorship status logic correctness
	@echo "✅ Verifying advisorship status logic..."
	@grep -B 3 '"end_date": "2017' data/exports/advisorships_canonical.json | grep status | head -3
	@grep -B 3 '"end_date": "2026' data/exports/advisorships_canonical.json | grep status | head -3

verify-exports: ## Check if all export files exist
	@echo "🔍 Verifying export files..."
	@ls -lh data/exports/*.json

audit-duplicates: ## Audit duplicate candidates in the current database
	@echo "🔎 Auditing duplicate candidates..."
	@$(PYTHON) src/scripts/audit_duplicates.py

harden-db: ## Create safe indexes/constraints for duplicate prevention
	@echo "🛡️ Hardening database indexes..."
	@$(PYTHON) src/scripts/harden_db_indices.py

consolidate-duplicates: ## Consolidate duplicate persons, teams, and knowledge areas
	@echo "🧹 Consolidating duplicate entities..."
	@$(PYTHON) src/scripts/consolidate_duplicates.py --entity all

consolidate-duplicates-dry: ## Preview duplicate consolidations without changing the database
	@echo "🧪 Previewing duplicate consolidation..."
	@$(PYTHON) src/scripts/consolidate_duplicates.py --entity all --dry-run

etl-report: ## Generate ETL extraction vs load reconciliation report
	@echo "📊 Generating ETL load report..."
	@$(PYTHON) src/scripts/etl_load_report.py

etl-report-md: ## Generate Markdown from the ETL JSON report
	@echo "📝 Generating ETL Markdown report..."
	@$(PYTHON) src/scripts/etl_report_markdown.py

tracking-audit-report: ## Generate tracking-domain audit report in JSON and Markdown
	@echo "🧾 Generating tracking audit report..."
	@$(PYTHON) src/scripts/tracking_audit_report.py

tracking-query: ## Query tracking data (use QUERY_ARGS="--entity-type researcher --entity-id 2981")
	@echo "🔎 Querying tracking data..."
	@$(PYTHON) src/scripts/tracking_query.py $(QUERY_ARGS)

# Development
logs-dir: ## Create logs directory if it doesn't exist
	@mkdir -p logs

setup: ## Initial project setup (for new developers)
	@echo "🔧 Setting up project..."
	@python3 -m venv .venv
	@$(PYTHON) -m pip install --upgrade pip
	@$(PYTHON) -m pip install -r requirements.txt
	@mkdir -p logs data/exports
	@echo "✅ Setup complete. Run 'make init-db' to initialize the database."

# Utility
clean: clean-db ## Clean all generated files and artifacts
	@echo "🧹 Cleaning artifacts..."
	@rm -rf __pycache__ .pytest_cache .coverage htmlcov
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean complete"

status: ## Show database and export status
	@echo "📊 Horizon ETL Status"
	@echo "===================="
	@echo "Database:"
	@ls -lh db/horizon.db 2>/dev/null || echo "  ❌ Not initialized"
	@echo ""
	@echo "Exports:"
	@ls -lh data/exports/*.json 2>/dev/null | wc -l | xargs -I {} echo "  {} files exported"
	@echo ""
	@echo "Last pipeline run:"
	@ls -lt logs/pipeline_*.log 2>/dev/null | head -1 || echo "  ❌ No logs found"

# Quick workflows
dev-cycle: format lint test ## Development cycle: format, lint, and test
	@echo "✅ Development cycle complete"

ci-check: format-check lint test ## CI validation checks
	@echo "✅ CI checks complete"

all: full-refresh verify-status ## Run everything: reset DB, pipeline, and verify
	@echo "🎉 All tasks complete!"

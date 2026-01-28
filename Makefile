# Horizon ETL - Makefile
# Project automation commands following @agile-standards

.PHONY: help clean-db init-db pipeline export test lint format all

# Python interpreter
PYTHON := .venv/bin/python3

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

# Pipeline Execution
pipeline: ## Run the full Serra campus pipeline
	@echo "🚀 Running Serra pipeline..."
	@$(PYTHON) src/flows/run_serra_pipeline.py

pipeline-log: ## Run pipeline with timestamped log output
	@echo "🚀 Running Serra pipeline with logging..."
	@$(PYTHON) src/flows/run_serra_pipeline.py 2>&1 | tee logs/pipeline_$$(date +%Y%m%d_%H%M%S).log

full-refresh: reset-db pipeline ## Complete refresh: clean DB + run full pipeline
	@echo "✅ Full refresh complete"

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

sync-cnpq: ## Sync CNPq data for Serra campus
	@echo "🔄 Syncing CNPq data..."
	@$(PYTHON) -c "from src.flows.sync_cnpq_groups import sync_cnpq_groups_flow; sync_cnpq_groups_flow(campus_name='Serra')"

# Export Operations
export: ## Export all canonical data
	@echo "📤 Exporting canonical data..."
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

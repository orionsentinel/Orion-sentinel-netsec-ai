# Orion Sentinel NetSec Node - Makefile
# Provides convenient commands for common operations

.PHONY: help setup install start-spog start-standalone stop status logs clean dev-install test lint format

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Orion Sentinel NetSec Node - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick Start:"
	@echo "  1. make setup          # Run interactive setup"
	@echo "  2. make start-spog     # Start in SPoG mode"
	@echo "     OR"
	@echo "     make start-standalone  # Start in Standalone mode"
	@echo ""

setup: ## Run interactive setup script
	@./setup.sh

install: setup ## Alias for setup

start-spog: ## Start services in SPoG mode (production)
	@./scripts/netsecctl.sh up-spog

start-standalone: ## Start services in Standalone mode (development/lab)
	@./scripts/netsecctl.sh up-standalone

start: start-spog ## Alias for start-spog (default start mode)

stop: ## Stop all services
	@./scripts/netsecctl.sh down

down: stop ## Alias for stop

status: ## Show status of all services
	@./scripts/netsecctl.sh status

logs: ## Tail logs from all services
	@./scripts/netsecctl.sh logs

restart-spog: stop start-spog ## Restart services in SPoG mode

restart-standalone: stop start-standalone ## Restart services in Standalone mode

dev-install: ## Set up Python development environment
	@echo "Setting up Python development environment..."
	@python3 -m venv venv
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install -e .
	@. venv/bin/activate && pip install -r requirements-dev.txt
	@echo "✅ Development environment ready!"
	@echo "Activate with: source venv/bin/activate"

test: ## Run tests
	@echo "Running tests..."
	@if [ -d "venv" ]; then \
		. venv/bin/activate && pytest tests/; \
	else \
		echo "Virtual environment not found. Run 'make dev-install' first."; \
		exit 1; \
	fi

lint: ## Run linters (ruff, mypy)
	@echo "Running linters..."
	@if [ -d "venv" ]; then \
		. venv/bin/activate && ruff check src/; \
		. venv/bin/activate && mypy src/; \
	else \
		echo "Virtual environment not found. Run 'make dev-install' first."; \
		exit 1; \
	fi

format: ## Format code with black
	@echo "Formatting code..."
	@if [ -d "venv" ]; then \
		. venv/bin/activate && black src/ tests/; \
	else \
		echo "Virtual environment not found. Run 'make dev-install' first."; \
		exit 1; \
	fi

clean: ## Clean up generated files and containers
	@echo "Cleaning up..."
	@./scripts/netsecctl.sh down || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

clean-all: clean ## Deep clean including venv and Docker volumes
	@echo "Performing deep clean..."
	@rm -rf venv
	@docker volume ls -q | grep orion | xargs -r docker volume rm || true
	@echo "✅ Deep clean complete"

env-check: ## Validate .env file exists and is configured
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "✅ .env file exists"
	@grep -q "LOKI_URL=http://192.168.8.XXX:3100" .env && \
		echo "⚠️  Warning: LOKI_URL still has default value. Update it in .env" || true

verify-spog: env-check ## Verify SPoG mode connectivity to CoreSrv
	@echo "Verifying SPoG mode connectivity..."
	@LOKI_URL=$$(grep LOKI_URL .env | cut -d= -f2); \
	if curl -s -o /dev/null -w "%{http_code}" $$LOKI_URL/ready | grep -q "200"; then \
		echo "✅ CoreSrv Loki is reachable at $$LOKI_URL"; \
	else \
		echo "❌ Cannot reach CoreSrv Loki at $$LOKI_URL"; \
		echo "   Check that CoreSrv is running and LOKI_URL in .env is correct"; \
		exit 1; \
	fi

health: ## Check health of running services
	@echo "Checking service health..."
	@docker ps --filter "name=orion-*" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

update-images: ## Pull latest Docker images
	@echo "Updating Docker images..."
	@cd stacks/nsm && docker compose pull
	@cd stacks/ai && docker compose pull
	@echo "✅ Images updated. Run 'make restart-spog' or 'make restart-standalone' to use new images"

backup-config: ## Backup .env and config files
	@echo "Backing up configuration..."
	@mkdir -p backups
	@tar -czf backups/config-backup-$$(date +%Y%m%d-%H%M%S).tar.gz .env config/
	@echo "✅ Configuration backed up to backups/"

.PHONY: docs
docs: ## Open documentation in browser (if available)
	@if command -v xdg-open > /dev/null; then \
		xdg-open README.md; \
	elif command -v open > /dev/null; then \
		open README.md; \
	else \
		echo "README.md - please open in your browser"; \
	fi

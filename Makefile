# Orion Sentinel NetSec Node - Makefile
# Provides convenient commands for common operations

.PHONY: help bootstrap setup install start-spog start-standalone start stop down status logs restart-spog restart-standalone dev-install test lint format clean clean-all env-check verify-spog health update-images backup-config docs up-core up-all

# Default target
.DEFAULT_GOAL := help

# Variables
NETSECCTL := ./scripts/netsecctl.sh
BOOTSTRAP := ./scripts/bootstrap-netsec.sh

help: ## Show this help message
	@echo "Orion Sentinel NetSec Node - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick Start (Production):"
	@echo "  1. make bootstrap      # Initial system setup"
	@echo "  2. make up-all         # Start all services (recommended)"
	@echo ""
	@echo "Alternative Quick Start:"
	@echo "  1. make setup          # Interactive setup (legacy)"
	@echo "  2. make start-spog     # Start in SPoG mode"
	@echo ""

bootstrap: ## Run bootstrap script to prepare system
	@$(BOOTSTRAP)

setup: ## Run interactive setup script (legacy)
	@./setup.sh

install: bootstrap ## Alias for bootstrap (recommended)

up-core: ## Start core NSM services only (netsec-core profile)
	@echo "Starting Orion Sentinel NetSec Core (Suricata + Promtail + Node Exporter)..."
	@docker compose --profile netsec-core up -d
	@echo "✓ Core services started"
	@echo "  Check status: make status"

up-all: ## Start all services (netsec-core + ai profiles) - RECOMMENDED
	@echo "Starting Orion Sentinel NetSec - Full Stack..."
	@docker compose --profile netsec-core --profile ai up -d
	@echo "✓ All services started"
	@echo "  Web UI: http://localhost:8000"
	@echo "  Check status: make status"

start-spog: ## Start services in SPoG mode (production) - LEGACY
	@$(NETSECCTL) up-spog

start-standalone: ## Start services in Standalone mode (development/lab) - LEGACY
	@$(NETSECCTL) up-standalone

start: up-all ## Alias for up-all (default start mode)

stop: ## Stop all services
	@echo "Stopping all Orion Sentinel services..."
	@docker compose --profile netsec-core --profile ai down
	@echo "✓ All services stopped"

down: stop ## Alias for stop

status: ## Show status of all services
	@echo "Orion Sentinel Service Status:"
	@echo ""
	@docker compose --profile netsec-core --profile ai ps

ps: status ## Alias for status - show running services

logs: ## Tail logs from all services
	@docker compose --profile netsec-core --profile ai logs -f --tail=100

restart-spog: stop start-spog ## Restart services in SPoG mode (legacy)

restart-standalone: stop start-standalone ## Restart services in Standalone mode (legacy)

restart: stop up-all ## Restart all services

dev-install: ## Set up Python development environment
	@echo "Setting up Python development environment..."
	@python3 -m venv venv
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install -e .
	@if [ -f requirements-dev.txt ]; then \
		. venv/bin/activate && pip install -r requirements-dev.txt; \
	else \
		echo "⚠️  requirements-dev.txt not found, skipping dev dependencies"; \
	fi
	@echo "✅ Development environment ready!"
	@echo "Activate with: source venv/bin/activate"

test: ## Run validation tests to check deployment
	@echo "=== Orion Sentinel Validation Tests ==="
	@echo ""
	@echo "1. Checking if services are running..."
	@docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "(orion-|NAME)" || echo "No services running"
	@echo ""
	@echo "2. Checking Suricata packet capture..."
	@docker exec orion-suricata suricatasc -c "capture-mode" 2>/dev/null || echo "  ⚠ Suricata not running or not responding"
	@echo ""
	@echo "3. Checking Promtail log shipping..."
	@docker logs orion-promtail 2>&1 | grep -i "POST" | tail -3 || echo "  ⚠ No log shipping activity found"
	@echo ""
	@echo "4. Checking API health..."
	@curl -s http://localhost:8000/api/health 2>/dev/null && echo "" || echo "  ⚠ API not responding"
	@echo ""
	@echo "✓ Validation complete. See above for any warnings."

test-python: ## Run Python unit tests
	@echo "Running Python unit tests..."
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
	@docker volume ls -q | grep -E '^(orion-sentinel-|orion-soar|orion-inventory)' | xargs -r docker volume rm || true
	@echo "✅ Deep clean complete"

env-check: ## Validate .env file exists and is configured
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "✅ .env file exists"
	@if [ -f .env.example ]; then \
		PLACEHOLDER=$$(grep "^LOKI_URL=" .env.example 2>/dev/null | cut -d= -f2 || echo ""); \
		CURRENT=$$(grep "^LOKI_URL=" .env 2>/dev/null | cut -d= -f2 || echo ""); \
		if [ -n "$$PLACEHOLDER" ] && [ "$$PLACEHOLDER" = "$$CURRENT" ]; then \
			echo "⚠️  Warning: LOKI_URL still has default value. Update it in .env"; \
		fi; \
	fi

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

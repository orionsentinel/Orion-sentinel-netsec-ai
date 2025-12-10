# Orion Sentinel NetSec Node - Makefile
# Provides convenient commands for common operations

.PHONY: help bootstrap check-nvme setup install up-minimal up-evebox up-debug up-full start stop down status logs restart dev-install test lint format clean clean-all env-check verify-spog health update-images backup-config backup-volumes restore-volume docs ps

# Default target
.DEFAULT_GOAL := help

# Variables
NETSECCTL := ./scripts/netsecctl.sh
BOOTSTRAP := ./scripts/bootstrap-netsec.sh
CHECK_NVME := ./scripts/check-nvme.sh

help: ## Show this help message
	@echo "Orion Sentinel NetSec Node - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick Start (Production - NVMe Deployment):"
	@echo "  1. make check-nvme     # Verify NVMe storage setup"
	@echo "  2. make bootstrap      # Initial system setup"
	@echo "  3. make up-minimal     # Start minimal NetSec sensor (recommended)"
	@echo ""
	@echo "Alternative Profiles:"
	@echo "  - make up-evebox       # Start with EveBox UI for local analysis"
	@echo "  - make up-full         # Start with legacy AI services (not recommended)"
	@echo ""

bootstrap: ## Run bootstrap script to prepare system
	@$(BOOTSTRAP)

check-nvme: ## Verify NVMe storage setup and health
	@echo "Checking NVMe storage..."
	@$(CHECK_NVME)

setup: ## Run interactive setup script (legacy)
	@./setup.sh

install: bootstrap ## Alias for bootstrap (recommended)

up-minimal: ## Start minimal NetSec sensor (Suricata + Promtail + Node Exporter) - PRODUCTION DEFAULT
	@echo "Starting Orion Sentinel NetSec - Minimal Profile (Production)..."
	@docker compose --profile netsec-minimal up -d
	@echo "✓ Minimal sensor started"
	@echo ""
	@echo "Services running:"
	@echo "  • Suricata IDS (passive monitoring)"
	@echo "  • Promtail (log shipping to CoreSrv)"
	@echo "  • Node Exporter (metrics on port 9100)"
	@echo ""
	@echo "Check status: make status"
	@echo "View logs: make logs"

up-evebox: ## Start NetSec with EveBox UI (minimal + local alert browsing)
	@echo "Starting Orion Sentinel NetSec - EveBox Profile..."
	@docker compose --profile netsec-plus-evebox up -d
	@echo "✓ NetSec with EveBox started"
	@echo ""
	@echo "Access EveBox UI: http://localhost:5636"
	@echo "Check status: make status"

up-debug: ## Start NetSec with debug tools (minimal + debug container)
	@echo "Starting Orion Sentinel NetSec - Debug Mode..."
	@docker compose --profile netsec-minimal --profile netsec-debug up -d
	@echo "✓ NetSec with debug tools started"
	@echo ""
	@echo "Access debug container:"
	@echo "  docker exec -it orion-netsec-debug /bin/sh"
	@echo ""
	@echo "Example debug commands:"
	@echo "  tcpdump -i eth0 -nn 'port 53'"
	@echo "  dig @8.8.8.8 google.com"
	@echo "  curl -v http://192.168.1.1"

up-full: ## Start full stack with legacy AI services (not recommended for production)
	@echo "⚠️  WARNING: Starting with legacy AI services"
	@echo "    For production, use 'make up-minimal' instead"
	@echo "    AI services should run on separate AI Node in v2"
	@echo ""
	@echo "Starting Orion Sentinel NetSec - Full Stack (Legacy)..."
	@docker compose --profile netsec-minimal --profile ai up -d
	@echo "✓ Full stack started"
	@echo ""
	@echo "  Web UI: http://localhost:8000"
	@echo "  Check status: make status"

# Legacy aliases for backward compatibility
up-core: up-minimal ## Alias for up-minimal (backward compatibility)

up-all: up-full ## Alias for up-full (backward compatibility)

start-spog: ## Start services in SPoG mode (production) - LEGACY
	@$(NETSECCTL) up-spog

start-standalone: ## Start services in Standalone mode (development/lab) - LEGACY
	@$(NETSECCTL) up-standalone

start: up-minimal ## Alias for up-minimal (default start mode)

stop: ## Stop all services
	@echo "Stopping all Orion Sentinel services..."
	@docker compose --profile netsec-minimal --profile netsec-plus-evebox --profile netsec-debug --profile ai down
	@echo "✓ All services stopped"

down: stop ## Alias for stop

status: ## Show status of all services
	@echo "Orion Sentinel Service Status:"
	@echo ""
	@docker compose ps

ps: status ## Alias for status - show running services

logs: ## Tail logs from all services
	@docker compose logs -f --tail=100

restart: stop up-minimal ## Restart minimal NetSec sensor

restart-spog: stop start-spog ## Restart services in SPoG mode (legacy)

restart-standalone: stop start-standalone ## Restart services in Standalone mode (legacy)

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
	@echo "=== Orion Sentinel NetSec Validation Tests ==="
	@echo ""
	@echo "1. Checking NVMe storage..."
	@$(CHECK_NVME) || echo "  ⚠ NVMe check failed"
	@echo ""
	@echo "2. Checking if services are running..."
	@docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "(orion-netsec|NAME)" || echo "  ⚠ No services running"
	@echo ""
	@echo "3. Checking Suricata packet capture..."
	@docker logs orion-netsec-suricata 2>&1 | grep -i "received" | tail -3 || echo "  ⚠ Suricata not running or no packets captured"
	@echo ""
	@echo "4. Checking Promtail log shipping..."
	@docker logs orion-netsec-promtail 2>&1 | grep -i "POST" | tail -3 || echo "  ⚠ No log shipping activity found"
	@echo ""
	@echo "5. Checking Node Exporter metrics..."
	@curl -s http://localhost:9100/metrics 2>/dev/null | head -5 && echo "  ✓ Node Exporter responding" || echo "  ⚠ Node Exporter not responding"
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

backup-volumes: ## Backup all Docker volumes (requires sudo)
	@echo "Backing up Docker volumes..."
	@sudo ./backup/backup-volumes.sh
	@echo "✅ Volume backup complete. See /srv/backups/orion/"

restore-volume: ## Restore a Docker volume (requires sudo and BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Error: BACKUP_FILE variable is required"; \
		echo "Usage: make restore-volume BACKUP_FILE=/path/to/backup.tar.gz"; \
		exit 1; \
	fi
	@echo "Restoring volume from $(BACKUP_FILE)..."
	@sudo ./backup/restore-volume.sh $(BACKUP_FILE)

.PHONY: docs
docs: ## Open documentation in browser (if available)
	@if command -v xdg-open > /dev/null; then \
		xdg-open README.md; \
	elif command -v open > /dev/null; then \
		open README.md; \
	else \
		echo "README.md - please open in your browser"; \
	fi

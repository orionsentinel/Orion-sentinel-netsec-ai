#!/usr/bin/env bash
#
# netsec-up.sh
# Start the Orion Sentinel NetSec stack with all pre-flight checks
#
# This script orchestrates the startup process:
# 1. Run NVMe health check and create directories
# 2. Tune host network interface
# 3. Sync Suricata config from repo to NVMe (if missing)
# 4. Start Docker Compose with netsec-minimal profile
#
# Environment variables:
#   NVME_MOUNT - NVMe mount path (default: /mnt/orion-nvme-netsec)
#   NETSEC_INTERFACE - Network interface to monitor (default: eth1)
#   COMPOSE_PROFILES - Additional compose profiles (default: netsec-minimal)
#   SKIP_MOUNT_CHECK - Skip NVMe mount verification (default: 0)
#
# Usage:
#   ./netsec-up.sh                     # Start with netsec-minimal profile
#   ./netsec-up.sh --with-evebox       # Start with netsec-plus-evebox profile
#   ./netsec-up.sh --skip-tune         # Skip host network tuning
#   ./netsec-up.sh --force-sync        # Force overwrite config files
#

set -euo pipefail

# Configuration
NVME_MOUNT="${NVME_MOUNT:-/mnt/orion-nvme-netsec}"
NETSEC_INTERFACE="${NETSEC_INTERFACE:-eth1}"
COMPOSE_PROFILE="${COMPOSE_PROFILES:-netsec-minimal}"

# Parse arguments
SKIP_TUNE=0
FORCE_SYNC=""
for arg in "$@"; do
    case $arg in
        --with-evebox)
            COMPOSE_PROFILE="netsec-plus-evebox"
            ;;
        --skip-tune)
            SKIP_TUNE=1
            ;;
        --force-sync)
            FORCE_SYNC="--force"
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-evebox   Start with EveBox UI (netsec-plus-evebox profile)"
            echo "  --skip-tune     Skip host network interface tuning"
            echo "  --force-sync    Force overwrite config files on NVMe"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
    esac
done

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}▶ $1${NC}"
    echo "────────────────────────────────────────────────"
}

# Step 1: NVMe health check
run_nvme_check() {
    log_step "Step 1: NVMe Health Check"
    
    export NVME_MOUNT
    export AUTO_CREATE_DIRS=1
    
    if "$SCRIPT_DIR/check-nvme.sh"; then
        log_info "NVMe check passed"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 2 ]; then
            log_warn "NVMe check passed with warnings"
            return 0
        else
            log_error "NVMe check failed"
            return 1
        fi
    fi
}

# Step 2: Host network tuning
run_host_tune() {
    log_step "Step 2: Host Network Tuning"
    
    if [ $SKIP_TUNE -eq 1 ]; then
        log_warn "Skipping host network tuning (--skip-tune)"
        return 0
    fi
    
    export NETSEC_INTERFACE
    
    if "$SCRIPT_DIR/netsec-host-tune.sh"; then
        log_info "Host network tuning complete"
        return 0
    else
        log_warn "Host network tuning had issues (non-fatal)"
        return 0  # Non-fatal
    fi
}

# Step 3: Config sync
run_config_sync() {
    log_step "Step 3: Suricata Config Sync"
    
    export NVME_MOUNT
    
    if "$SCRIPT_DIR/netsec-sync-config.sh" $FORCE_SYNC; then
        log_info "Config sync complete"
        return 0
    else
        log_error "Config sync failed"
        return 1
    fi
}

# Step 4: Docker Compose up
run_compose_up() {
    log_step "Step 4: Starting Docker Compose"
    
    cd "$PROJECT_ROOT"
    
    log_info "Profile: $COMPOSE_PROFILE"
    log_info "Running: docker compose --profile $COMPOSE_PROFILE up -d"
    echo ""
    
    if docker compose --profile "$COMPOSE_PROFILE" up -d; then
        log_info "Docker Compose started successfully"
        return 0
    else
        log_error "Docker Compose failed to start"
        return 1
    fi
}

# Show status
show_status() {
    log_step "Stack Status"
    
    cd "$PROJECT_ROOT"
    
    docker compose --profile "$COMPOSE_PROFILE" ps
    
    echo ""
    log_info "Waiting for Suricata to initialize (10 seconds)..."
    sleep 10
    
    echo ""
    log_info "Recent Suricata logs:"
    docker logs --tail 10 orion-netsec-suricata 2>&1 || true
    
    echo ""
    log_info "Checking for eve.json..."
    if [ -f "$NVME_MOUNT/suricata/logs/eve.json" ]; then
        log_info "eve.json exists: $NVME_MOUNT/suricata/logs/eve.json"
        local size
        size=$(ls -lh "$NVME_MOUNT/suricata/logs/eve.json" 2>/dev/null | awk '{print $5}' || echo "unknown")
        log_info "Size: $size"
    else
        log_warn "eve.json not found yet - may take a moment to appear"
    fi
}

# Main execution
main() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Orion Sentinel NetSec Pi - Stack Startup               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Configuration:"
    echo "  NVME_MOUNT:        $NVME_MOUNT"
    echo "  NETSEC_INTERFACE:  $NETSEC_INTERFACE"
    echo "  COMPOSE_PROFILE:   $COMPOSE_PROFILE"
    
    # Step 1: NVMe check
    if ! run_nvme_check; then
        log_error "Aborting startup due to NVMe check failure"
        exit 1
    fi
    
    # Step 2: Host tuning
    run_host_tune
    
    # Step 3: Config sync
    if ! run_config_sync; then
        log_error "Aborting startup due to config sync failure"
        exit 1
    fi
    
    # Step 4: Docker Compose
    if ! run_compose_up; then
        log_error "Aborting startup due to Docker Compose failure"
        exit 1
    fi
    
    # Show status
    show_status
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                 Startup Complete! ✓                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Quick commands:"
    echo "  View logs:     docker logs -f orion-netsec-suricata"
    echo "  View alerts:   tail -f $NVME_MOUNT/suricata/logs/eve.json | jq 'select(.event_type==\"alert\")'"
    echo "  Update rules:  ./scripts/suricata-update.sh"
    echo "  Validate:      ./scripts/validate-netsec.sh"
    echo "  Stop stack:    docker compose --profile $COMPOSE_PROFILE down"
    echo ""
}

# Run main function
main "$@"

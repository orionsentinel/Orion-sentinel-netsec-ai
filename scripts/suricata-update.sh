#!/usr/bin/env bash
#
# suricata-update.sh
# Update Suricata rules and restart the container
#
# This script:
# 1. Runs suricata-update inside the container to fetch latest rules
#    - Uses /etc/suricata/disable.conf to disable problematic rules
#    - Writes rules to /var/lib/suricata/rules/suricata.rules
# 2. Tests the configuration with suricata -T
# 3. Restarts the container if the config test passes
#
# Note: suricata-update's hot reload via unix-command socket may not work
# in all configurations. A container restart is the most reliable method.
#
# Usage:
#   ./suricata-update.sh              # Update and restart if valid
#   ./suricata-update.sh --no-restart # Update only, no restart
#

set -euo pipefail

# Configuration
CONTAINER_NAME="${SURICATA_CONTAINER:-orion-netsec-suricata}"
NO_RESTART="${1:-}"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
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

# Check if container is running
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Suricata container '$CONTAINER_NAME' is not running"
        log_error "Start it with: docker compose --profile netsec-minimal up -d"
        return 1
    fi
    log_info "Suricata container '$CONTAINER_NAME' is running"
    return 0
}

# Run suricata-update
run_suricata_update() {
    log_info "Running suricata-update..."
    log_info "Using disable.conf to filter problematic rules (DNP3, Modbus, test rules)"
    echo ""
    
    # Run suricata-update with disable.conf
    # --disable-conf: Path to disable.conf file for filtering rules
    # --output-dir: Write rules to /var/lib/suricata/rules
    # This ensures suricata.rules is written to the correct location
    if docker exec -t "$CONTAINER_NAME" suricata-update \
        --disable-conf /etc/suricata/disable.conf \
        --output-dir /var/lib/suricata/rules; then
        echo ""
        log_info "suricata-update completed successfully"
        return 0
    else
        echo ""
        log_error "suricata-update failed"
        return 1
    fi
}

# Test Suricata configuration
test_config() {
    log_info "Testing Suricata configuration..."
    echo ""
    
    if docker exec -t "$CONTAINER_NAME" suricata -T -c /etc/suricata/suricata.yaml 2>&1; then
        echo ""
        log_info "Configuration test PASSED"
        return 0
    else
        echo ""
        log_error "Configuration test FAILED"
        log_error "Fix configuration errors before restarting"
        return 1
    fi
}

# Restart container
restart_container() {
    log_info "Restarting Suricata container..."
    
    if docker restart "$CONTAINER_NAME"; then
        log_info "Container restarted successfully"
        
        # Wait for startup
        log_info "Waiting for Suricata to initialize..."
        sleep 5
        
        # Check container is running
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            log_info "Suricata is running"
            
            # Show recent logs
            echo ""
            log_info "Recent container logs:"
            docker logs --tail 20 "$CONTAINER_NAME" 2>&1 | tail -15
            
            return 0
        else
            log_error "Container failed to start after restart"
            log_error "Check logs: docker logs $CONTAINER_NAME"
            return 1
        fi
    else
        log_error "Failed to restart container"
        return 1
    fi
}

# Show rules statistics
show_rules_stats() {
    log_info "Checking loaded rules..."
    
    # Try to get rule count from logs
    local rule_count
    rule_count=$(docker logs --tail 100 "$CONTAINER_NAME" 2>&1 | grep -oE 'Loaded [0-9]+ rules' | tail -1 || echo "")
    
    if [ -n "$rule_count" ]; then
        log_info "$rule_count"
    fi
    
    # Check if rules file exists
    if docker exec "$CONTAINER_NAME" test -f /var/lib/suricata/rules/suricata.rules 2>/dev/null; then
        local line_count
        line_count=$(docker exec "$CONTAINER_NAME" wc -l /var/lib/suricata/rules/suricata.rules 2>/dev/null | awk '{print $1}' || echo "unknown")
        log_info "Rules file has $line_count lines"
    fi
    
    # Check disable.conf is being used
    if docker exec "$CONTAINER_NAME" test -f /etc/suricata/disable.conf 2>/dev/null; then
        log_info "✓ disable.conf is mounted and available"
    else
        log_warn "⚠ disable.conf not found - some rules may cause parse errors"
    fi
}

# Main execution
main() {
    echo "================================================"
    echo "Orion Sentinel NetSec Pi - Suricata Rule Update"
    echo "================================================"
    echo ""
    
    # Check container is running
    if ! check_container; then
        exit 1
    fi
    
    # Run suricata-update
    if ! run_suricata_update; then
        exit 1
    fi
    
    # Test configuration
    if ! test_config; then
        exit 1
    fi
    
    # Restart unless --no-restart specified
    if [ "$NO_RESTART" = "--no-restart" ]; then
        log_warn "Skipping restart (--no-restart specified)"
        log_warn "Rules will be loaded on next container restart"
    else
        echo ""
        if ! restart_container; then
            exit 1
        fi
    fi
    
    echo ""
    show_rules_stats
    
    echo ""
    echo "================================================"
    log_info "Suricata rule update complete"
    echo ""
    echo "To verify rules are working:"
    echo "  curl https://testmyids.com"
    echo "  docker exec $CONTAINER_NAME tail -f /var/log/suricata/eve.json | jq 'select(.event_type==\"alert\")'"
}

# Run main function
main "$@"

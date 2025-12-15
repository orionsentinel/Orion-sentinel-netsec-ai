#!/usr/bin/env bash
#
# validate-netsec.sh
# Validate that the Orion Sentinel NetSec stack is running correctly
#
# This script checks:
# 1. Suricata container is Up
# 2. Suricata config test passes (suricata -T)
# 3. No recent startup errors in logs
# 4. eve.json exists and is being written to
#
# Environment variables:
#   NVME_MOUNT - NVMe mount path (default: /mnt/orion-nvme-netsec)
#
# Exit codes:
#   0 = All checks passed
#   1 = One or more checks failed
#
# Usage:
#   ./validate-netsec.sh          # Run all validations
#   ./validate-netsec.sh --quick  # Quick check (container + eve.json only)
#

set -euo pipefail

# Configuration
NVME_MOUNT="${NVME_MOUNT:-/mnt/orion-nvme-netsec}"
CONTAINER_NAME="${SURICATA_CONTAINER:-orion-netsec-suricata}"
QUICK_MODE="${1:-}"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Logging functions
log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

log_info() {
    echo -e "       $1"
}

# Check 1: Container is running
check_container_running() {
    echo ""
    echo "Check 1: Suricata container status"
    echo "──────────────────────────────────"
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        local status
        status=$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        local uptime
        uptime=$(docker inspect --format '{{.State.StartedAt}}' "$CONTAINER_NAME" 2>/dev/null | cut -d'T' -f1 || echo "unknown")
        
        log_pass "Container '$CONTAINER_NAME' is running (status: $status)"
        log_info "Started: $uptime"
        return 0
    else
        log_fail "Container '$CONTAINER_NAME' is NOT running"
        log_info "Start with: docker compose --profile netsec-minimal up -d"
        return 1
    fi
}

# Check 2: Config test passes
check_config_test() {
    echo ""
    echo "Check 2: Suricata configuration test"
    echo "─────────────────────────────────────"
    
    local output
    local exit_code=0
    
    output=$(docker exec "$CONTAINER_NAME" suricata -T -c /etc/suricata/suricata.yaml 2>&1) || exit_code=$?
    
    # Show last 5 lines of output
    echo "$output" | tail -5
    
    if [ $exit_code -eq 0 ]; then
        log_pass "Configuration test passed"
        return 0
    fi
    
    log_fail "Configuration test failed"
    log_info "Check config with: docker exec $CONTAINER_NAME suricata -T -c /etc/suricata/suricata.yaml"
    return 1
}

# Check 3: No startup errors
check_no_errors() {
    echo ""
    echo "Check 3: Recent log errors"
    echo "──────────────────────────"
    
    local error_patterns=(
        "malformed integer"
        "failed to mmap"
        "failed to init socket"
        "no rules were loaded"
        "Error opening"
        "Permission denied"
        "fanout not supported"
        "Configuration node.*redefined"
    )
    
    local logs
    logs=$(docker logs --tail 100 "$CONTAINER_NAME" 2>&1 || echo "")
    
    local found_errors=0
    for pattern in "${error_patterns[@]}"; do
        if echo "$logs" | grep -qi "$pattern"; then
            log_fail "Found error: $pattern"
            echo "$logs" | grep -i "$pattern" | head -2 | while read -r line; do
                log_info "  $line"
            done
            found_errors=1
        fi
    done
    
    if [ $found_errors -eq 0 ]; then
        log_pass "No startup errors found in recent logs"
        return 0
    fi
    
    return 1
}

# Check 4: eve.json exists and is growing
check_eve_json() {
    echo ""
    echo "Check 4: EVE JSON output"
    echo "────────────────────────"
    
    local eve_path="$NVME_MOUNT/suricata/logs/eve.json"
    
    if [ ! -f "$eve_path" ]; then
        log_fail "eve.json does not exist at $eve_path"
        log_info "This may be normal if Suricata just started"
        return 1
    fi
    
    local size
    size=$(stat -c%s "$eve_path" 2>/dev/null || echo "0")
    local human_size
    human_size=$(ls -lh "$eve_path" 2>/dev/null | awk '{print $5}' || echo "unknown")
    
    if [ "$size" -eq 0 ]; then
        log_warn "eve.json exists but is empty"
        log_info "This may be normal if no traffic has been captured yet"
        return 0
    fi
    
    log_pass "eve.json exists and has data"
    log_info "Size: $human_size ($size bytes)"
    
    # Check if file was modified recently
    local modified
    modified=$(stat -c%Y "$eve_path" 2>/dev/null || echo "0")
    local now
    now=$(date +%s)
    local age=$((now - modified))
    
    if [ $age -lt 300 ]; then
        log_pass "eve.json was modified in the last 5 minutes"
    else
        log_warn "eve.json has not been modified in $age seconds"
        log_info "This may indicate no traffic is being captured"
    fi
    
    # Show last event
    echo ""
    log_info "Last event:"
    local last_event
    last_event=$(tail -1 "$eve_path" 2>/dev/null || echo "")
    if [ -n "$last_event" ]; then
        echo "$last_event" | jq -c '.' 2>/dev/null || echo "$last_event" | head -c 200
    fi
    
    return 0
}

# Check 5: Rules loaded
check_rules_loaded() {
    echo ""
    echo "Check 5: Rules loaded"
    echo "─────────────────────"
    
    local logs
    logs=$(docker logs --tail 200 "$CONTAINER_NAME" 2>&1 || echo "")
    
    local rule_count
    rule_count=$(echo "$logs" | grep -oE 'Loaded [0-9]+ rules' | tail -1 || echo "")
    
    if [ -n "$rule_count" ]; then
        log_pass "$rule_count"
        return 0
    fi
    
    # Check if rules file exists
    if docker exec "$CONTAINER_NAME" test -f /var/lib/suricata/rules/suricata.rules 2>/dev/null; then
        local line_count
        line_count=$(docker exec "$CONTAINER_NAME" wc -l /var/lib/suricata/rules/suricata.rules 2>/dev/null | awk '{print $1}' || echo "0")
        if [ "$line_count" -gt 0 ]; then
            log_pass "Rules file exists with $line_count lines"
            return 0
        fi
    fi
    
    log_warn "Could not determine rules status"
    log_info "Run: ./scripts/suricata-update.sh to update rules"
    return 0
}

# Check 6: Node exporter accessible
check_node_exporter() {
    echo ""
    echo "Check 6: Node Exporter"
    echo "──────────────────────"
    
    local port="${NODE_EXPORTER_PORT:-19100}"
    
    if curl -s --connect-timeout 2 "http://localhost:$port/metrics" | head -5 &>/dev/null; then
        log_pass "Node Exporter is accessible on port $port"
        return 0
    else
        log_warn "Node Exporter not accessible on port $port"
        log_info "This is non-critical if using a different port or not enabled"
        return 0
    fi
}

# Check 7: Promtail running
check_promtail() {
    echo ""
    echo "Check 7: Promtail status"
    echo "────────────────────────"
    
    local promtail_container="orion-netsec-promtail"
    
    if docker ps --format '{{.Names}}' | grep -q "^${promtail_container}$"; then
        log_pass "Promtail container is running"
        
        # Check for successful pushes in logs
        local logs
        logs=$(docker logs --tail 50 "$promtail_container" 2>&1 || echo "")
        
        if echo "$logs" | grep -qi "200 OK\|level=info\|pushing"; then
            log_pass "Promtail appears to be shipping logs"
        else
            log_warn "Could not confirm Promtail is shipping logs"
        fi
        return 0
    else
        log_warn "Promtail container is not running"
        log_info "Logs will not be shipped to Loki"
        return 0
    fi
}

# Summary
show_summary() {
    echo ""
    echo "════════════════════════════════════════════════"
    echo "                  SUMMARY"
    echo "════════════════════════════════════════════════"
    echo ""
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${RED}Failed:${NC}   $FAILED"
    echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All critical checks passed!${NC}"
        if [ $WARNINGS -gt 0 ]; then
            echo -e "${YELLOW}  Review warnings above for potential improvements.${NC}"
        fi
        return 0
    else
        echo -e "${RED}✗ Some checks failed. Review the output above.${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     Orion Sentinel NetSec Pi - Stack Validation            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    
    # Quick mode: only container + eve.json
    if [ "$QUICK_MODE" = "--quick" ]; then
        check_container_running || true
        check_eve_json || true
        show_summary
        exit $?
    fi
    
    # Full validation
    check_container_running || true
    
    # Only run remaining checks if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        check_config_test || true
        check_no_errors || true
        check_rules_loaded || true
    fi
    
    check_eve_json || true
    check_node_exporter || true
    check_promtail || true
    
    show_summary
    
    if [ $FAILED -gt 0 ]; then
        exit 1
    fi
    exit 0
}

# Run main function
main "$@"

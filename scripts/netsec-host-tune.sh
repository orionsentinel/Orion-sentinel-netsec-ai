#!/usr/bin/env bash
#
# netsec-host-tune.sh
# Host network interface tuning for Orion Sentinel NetSec Pi
#
# This script prepares the network interface for passive packet capture by:
# 1. Enabling promiscuous mode on the monitoring interface
# 2. Disabling hardware offloads that can interfere with packet capture
#
# Environment variables:
#   NETSEC_INTERFACE - Network interface to tune (default: eth1)
#
# Usage:
#   ./netsec-host-tune.sh           # Tune default interface (eth1)
#   NETSEC_INTERFACE=eth0 ./netsec-host-tune.sh  # Tune specific interface
#

set -euo pipefail

# Configuration
NETSEC_INTERFACE="${NETSEC_INTERFACE:-eth1}"

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

# Check if interface exists
check_interface() {
    if ! ip link show "$NETSEC_INTERFACE" &>/dev/null; then
        log_error "Interface '$NETSEC_INTERFACE' does not exist"
        log_error "Available interfaces:"
        ip link show | grep -E '^\d+:' | awk '{print "  " $2}' | tr -d ':'
        return 1
    fi
    log_info "Interface '$NETSEC_INTERFACE' exists"
    return 0
}

# Enable promiscuous mode
enable_promisc() {
    log_info "Enabling promiscuous mode on $NETSEC_INTERFACE..."
    
    if ip link set "$NETSEC_INTERFACE" promisc on 2>/dev/null; then
        log_info "Promiscuous mode enabled on $NETSEC_INTERFACE"
        return 0
    elif sudo ip link set "$NETSEC_INTERFACE" promisc on 2>/dev/null; then
        log_info "Promiscuous mode enabled on $NETSEC_INTERFACE (sudo)"
        return 0
    else
        log_warn "Failed to enable promiscuous mode on $NETSEC_INTERFACE"
        log_warn "This may require root privileges or the interface may not support it"
        return 0  # Non-fatal
    fi
}

# Disable hardware offloads that can interfere with packet capture
disable_offloads() {
    log_info "Disabling hardware offloads on $NETSEC_INTERFACE..."
    
    # Check if ethtool is available
    if ! command -v ethtool &>/dev/null; then
        log_warn "ethtool not found, skipping offload configuration"
        log_warn "Install with: sudo apt-get install ethtool"
        return 0  # Non-fatal
    fi
    
    # Offloads to disable (best effort - some may not be supported)
    local offloads=("gro" "lro" "gso" "tso")
    
    for offload in "${offloads[@]}"; do
        if ethtool -K "$NETSEC_INTERFACE" "$offload" off 2>/dev/null; then
            log_info "Disabled $offload on $NETSEC_INTERFACE"
        elif sudo ethtool -K "$NETSEC_INTERFACE" "$offload" off 2>/dev/null; then
            log_info "Disabled $offload on $NETSEC_INTERFACE (sudo)"
        else
            # This is expected for interfaces that don't support these features
            log_warn "Could not disable $offload on $NETSEC_INTERFACE (may not be supported)"
        fi
    done
    
    return 0
}

# Show current interface status
show_interface_status() {
    log_info "Current interface status for $NETSEC_INTERFACE:"
    
    # Show link status
    ip link show "$NETSEC_INTERFACE" 2>/dev/null || true
    
    # Show IP address (if any)
    ip addr show "$NETSEC_INTERFACE" 2>/dev/null | grep -E 'inet|inet6' || true
    
    # Show offload settings (if ethtool available)
    if command -v ethtool &>/dev/null; then
        echo ""
        log_info "Offload settings:"
        # Show relevant offload features (gso, tso, gro, lro)
        ethtool -k "$NETSEC_INTERFACE" 2>/dev/null | grep -E '(gso|tso|gro|lro):' || true
    fi
}

# Bring interface up if down
bring_interface_up() {
    local state
    state=$(ip link show "$NETSEC_INTERFACE" | grep -oE 'state [A-Z]+' | awk '{print $2}')
    
    if [ "$state" = "DOWN" ]; then
        log_info "Interface $NETSEC_INTERFACE is DOWN, bringing it up..."
        if ip link set "$NETSEC_INTERFACE" up 2>/dev/null; then
            log_info "Interface $NETSEC_INTERFACE is now UP"
        elif sudo ip link set "$NETSEC_INTERFACE" up 2>/dev/null; then
            log_info "Interface $NETSEC_INTERFACE is now UP (sudo)"
        else
            log_warn "Failed to bring up interface $NETSEC_INTERFACE"
        fi
    else
        log_info "Interface $NETSEC_INTERFACE is $state"
    fi
}

# Main execution
main() {
    echo "================================================"
    echo "Orion Sentinel NetSec Pi - Host Network Tuning"
    echo "================================================"
    echo ""
    echo "Target interface: $NETSEC_INTERFACE"
    echo ""
    
    # Check interface exists
    if ! check_interface; then
        exit 1
    fi
    
    # Bring interface up if needed
    bring_interface_up
    
    # Enable promiscuous mode
    enable_promisc
    
    # Disable offloads
    disable_offloads
    
    echo ""
    show_interface_status
    
    echo ""
    echo "================================================"
    log_info "Host network tuning complete"
    echo ""
    echo "Note: These settings may not persist across reboots."
    echo "Consider adding them to /etc/rc.local or a systemd service."
}

# Run main function
main "$@"

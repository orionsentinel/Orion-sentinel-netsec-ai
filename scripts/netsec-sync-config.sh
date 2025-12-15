#!/usr/bin/env bash
#
# netsec-sync-config.sh
# Synchronize Suricata configuration from repository to NVMe
#
# This script ensures the NVMe-mounted /etc/suricata directory has all
# required configuration files. It copies files from the repository template
# if they don't exist on NVMe.
#
# By default, it will NOT overwrite existing files. Use --force to overwrite.
#
# Environment variables:
#   NVME_MOUNT - NVMe mount path (default: /mnt/orion-nvme-netsec)
#
# Usage:
#   ./netsec-sync-config.sh          # Sync only missing files
#   ./netsec-sync-config.sh --force  # Force overwrite all files
#

set -euo pipefail

# Configuration
NVME_MOUNT="${NVME_MOUNT:-/mnt/orion-nvme-netsec}"
FORCE_OVERWRITE="${1:-}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source and destination paths
SRC_CONFIG_DIR="$PROJECT_ROOT/config/suricata"
DEST_CONFIG_DIR="$NVME_MOUNT/suricata/etc"

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

# Check prerequisites
check_prerequisites() {
    # Check source directory exists
    if [ ! -d "$SRC_CONFIG_DIR" ]; then
        log_error "Source config directory not found: $SRC_CONFIG_DIR"
        return 1
    fi
    
    # Check destination directory exists
    if [ ! -d "$DEST_CONFIG_DIR" ]; then
        log_warn "Destination directory does not exist: $DEST_CONFIG_DIR"
        log_info "Creating destination directory..."
        if mkdir -p "$DEST_CONFIG_DIR" 2>/dev/null; then
            log_info "Created: $DEST_CONFIG_DIR"
        elif sudo mkdir -p "$DEST_CONFIG_DIR" 2>/dev/null; then
            log_info "Created (sudo): $DEST_CONFIG_DIR"
        else
            log_error "Failed to create destination directory"
            return 1
        fi
    fi
    
    return 0
}

# Sync a single file
sync_file() {
    local src="$1"
    local filename
    filename=$(basename "$src")
    local dest="$DEST_CONFIG_DIR/$filename"
    
    if [ -f "$dest" ] && [ "$FORCE_OVERWRITE" != "--force" ]; then
        log_info "Skipping (exists): $filename"
        return 0
    fi
    
    local action="Creating"
    if [ -f "$dest" ]; then
        action="Overwriting"
    fi
    
    if cp "$src" "$dest" 2>/dev/null; then
        log_info "$action: $filename"
    elif sudo cp "$src" "$dest" 2>/dev/null; then
        log_info "$action (sudo): $filename"
    else
        log_error "Failed to copy: $filename"
        return 1
    fi
    
    return 0
}

# Create default config files if they don't exist in source
create_default_configs() {
    # classification.config - required by Suricata
    if [ ! -f "$DEST_CONFIG_DIR/classification.config" ]; then
        log_info "Creating default classification.config..."
        cat > /tmp/classification.config << 'EOF'
# Suricata Classification Configuration
# Format: config classification: name,description,priority

config classification: not-suspicious,Not Suspicious Traffic,3
config classification: unknown,Unknown Traffic,3
config classification: bad-unknown,Potentially Bad Traffic,2
config classification: attempted-recon,Attempted Information Leak,2
config classification: successful-recon-limited,Information Leak,2
config classification: successful-recon-largescale,Large Scale Information Leak,2
config classification: attempted-dos,Attempted Denial of Service,2
config classification: successful-dos,Denial of Service,2
config classification: attempted-user,Attempted User Privilege Gain,1
config classification: unsuccessful-user,Unsuccessful User Privilege Gain,1
config classification: successful-user,Successful User Privilege Gain,1
config classification: attempted-admin,Attempted Administrator Privilege Gain,1
config classification: successful-admin,Successful Administrator Privilege Gain,1
config classification: rpc-portmap-decode,Decode of an RPC Query,2
config classification: shellcode-detect,Executable Code was Detected,1
config classification: string-detect,A Suspicious String was Detected,3
config classification: suspicious-filename-detect,A Suspicious Filename was Detected,2
config classification: suspicious-login,An Attempted Login Using a Suspicious Username was Detected,2
config classification: system-call-detect,A System Call was Detected,2
config classification: tcp-connection,A TCP Connection was Detected,4
config classification: trojan-activity,A Network Trojan was Detected,1
config classification: unusual-client-port-connection,A Client was Using an Unusual Port,2
config classification: network-scan,Detection of a Network Scan,3
config classification: denial-of-service,Detection of a Denial of Service Attack,2
config classification: non-standard-protocol,Detection of a Non-Standard Protocol or Event,2
config classification: protocol-command-decode,Generic Protocol Command Decode,3
config classification: web-application-activity,Access to a Potentially Vulnerable Web Application,2
config classification: web-application-attack,Web Application Attack,1
config classification: misc-activity,Misc activity,3
config classification: misc-attack,Misc Attack,2
config classification: icmp-event,Generic ICMP event,3
config classification: inappropriate-content,Inappropriate Content was Detected,1
config classification: policy-violation,Potential Corporate Privacy Violation,1
config classification: default-login-attempt,Attempt to Login By a Default Username and Password,2
config classification: sdf,Sensitive Data,2
config classification: file-format,Known malicious file or file based exploit,1
config classification: malware-cnc,Known malware command and control traffic,1
config classification: client-side-exploit,Known client side exploit attempt,1
EOF
        if cp /tmp/classification.config "$DEST_CONFIG_DIR/classification.config" 2>/dev/null || \
           sudo cp /tmp/classification.config "$DEST_CONFIG_DIR/classification.config" 2>/dev/null; then
            log_info "Created: classification.config"
        fi
        rm -f /tmp/classification.config
    fi
    
    # reference.config - required by Suricata
    if [ ! -f "$DEST_CONFIG_DIR/reference.config" ]; then
        log_info "Creating default reference.config..."
        cat > /tmp/reference.config << 'EOF'
# Suricata Reference Configuration
# Format: config reference: name url

config reference: bugtraq   http://www.securityfocus.com/bid/
config reference: cve       http://cve.mitre.org/cgi-bin/cvename.cgi?name=
config reference: nessus    http://cgi.nessus.org/plugins/dump.php3?id=
config reference: arachnids http://www.whitehats.com/info/IDS
config reference: mcafee    http://vil.nai.com/vil/content/v_
config reference: osvdb     http://osvdb.org/show/osvdb/
config reference: msb       http://technet.microsoft.com/en-us/security/bulletin/
config reference: url       http://
EOF
        if cp /tmp/reference.config "$DEST_CONFIG_DIR/reference.config" 2>/dev/null || \
           sudo cp /tmp/reference.config "$DEST_CONFIG_DIR/reference.config" 2>/dev/null; then
            log_info "Created: reference.config"
        fi
        rm -f /tmp/reference.config
    fi
    
    # threshold.config - required by Suricata (can be empty)
    if [ ! -f "$DEST_CONFIG_DIR/threshold.config" ]; then
        log_info "Creating default threshold.config..."
        cat > /tmp/threshold.config << 'EOF'
# Suricata Threshold Configuration
# Use this file to suppress or rate-limit specific alerts
#
# Format examples:
# suppress gen_id <gid>, sig_id <sid>
# suppress gen_id <gid>, sig_id <sid>, track by_src, ip <ip>
# threshold gen_id <gid>, sig_id <sid>, type limit, track by_src, count 1, seconds 60
#
# See: https://suricata.readthedocs.io/en/latest/configuration/thresholding.html
EOF
        if cp /tmp/threshold.config "$DEST_CONFIG_DIR/threshold.config" 2>/dev/null || \
           sudo cp /tmp/threshold.config "$DEST_CONFIG_DIR/threshold.config" 2>/dev/null; then
            log_info "Created: threshold.config"
        fi
        rm -f /tmp/threshold.config
    fi
}

# Set proper ownership
set_ownership() {
    log_info "Setting ownership to UID 1000..."
    if chown -R 1000:1000 "$DEST_CONFIG_DIR" 2>/dev/null; then
        log_info "Ownership set successfully"
    elif sudo chown -R 1000:1000 "$DEST_CONFIG_DIR" 2>/dev/null; then
        log_info "Ownership set successfully (sudo)"
    else
        log_warn "Could not set ownership - may cause permission issues"
    fi
}

# Main execution
main() {
    echo "================================================"
    echo "Orion Sentinel NetSec Pi - Config Sync"
    echo "================================================"
    echo ""
    echo "Source:      $SRC_CONFIG_DIR"
    echo "Destination: $DEST_CONFIG_DIR"
    if [ "$FORCE_OVERWRITE" = "--force" ]; then
        echo "Mode:        Force overwrite"
    else
        echo "Mode:        Skip existing files"
    fi
    echo ""
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Sync files from source
    log_info "Syncing configuration files..."
    
    # Sync suricata.yaml
    if [ -f "$SRC_CONFIG_DIR/suricata.yaml" ]; then
        sync_file "$SRC_CONFIG_DIR/suricata.yaml"
    else
        log_error "suricata.yaml not found in $SRC_CONFIG_DIR"
        exit 1
    fi
    
    # Sync disable.conf
    if [ -f "$SRC_CONFIG_DIR/disable.conf" ]; then
        sync_file "$SRC_CONFIG_DIR/disable.conf"
    else
        log_warn "disable.conf not found in $SRC_CONFIG_DIR"
    fi
    
    # Create default support files if needed
    create_default_configs
    
    # Set ownership
    set_ownership
    
    echo ""
    echo "================================================"
    log_info "Config sync complete"
    echo ""
    echo "Files in $DEST_CONFIG_DIR:"
    ls -la "$DEST_CONFIG_DIR" 2>/dev/null || sudo ls -la "$DEST_CONFIG_DIR"
}

# Run main function
main "$@"

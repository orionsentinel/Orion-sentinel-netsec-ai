#!/usr/bin/env bash
#
# check-nvme.sh
# Pre-flight check script for Orion Sentinel NetSec Pi NVMe storage
#
# This script verifies that:
# 1. NVMe mount point exists
# 2. NVMe is actually mounted (not just an empty directory)
# 3. NVMe has sufficient free space
# 4. Required directories exist with proper permissions
#
# Environment variables:
#   NVME_MOUNT_POINT - NVMe mount path (default: /mnt/orion-nvme-netsec)
#   NVME_WARN_THRESHOLD - Warn percentage (default: 80)
#   NVME_CRITICAL_THRESHOLD - Critical percentage (default: 95)
#   AUTO_CREATE_DIRS - Auto-create missing directories without prompting (default: 0)
#
# Exit codes:
#   0 = All checks passed
#   1 = Critical error (mount missing or full)
#   2 = Warning (low disk space but not critical)
#
# Usage:
#   ./check-nvme.sh                    # Interactive mode
#   AUTO_CREATE_DIRS=1 ./check-nvme.sh # Non-interactive mode
#

set -euo pipefail

# Configuration
NVME_MOUNT_POINT="${NVME_MOUNT_POINT:-/mnt/orion-nvme-netsec}"
WARN_THRESHOLD_PCT="${NVME_WARN_THRESHOLD:-80}"
CRITICAL_THRESHOLD_PCT="${NVME_CRITICAL_THRESHOLD:-95}"

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

# Function to check if mount point exists
check_mount_exists() {
    if [ ! -d "$NVME_MOUNT_POINT" ]; then
        log_error "NVMe mount point does not exist: $NVME_MOUNT_POINT"
        log_error "Create it with: sudo mkdir -p $NVME_MOUNT_POINT"
        return 1
    fi
    log_info "NVMe mount point exists: $NVME_MOUNT_POINT"
    return 0
}

# Function to check if NVMe is actually mounted
check_is_mounted() {
    if ! mountpoint -q "$NVME_MOUNT_POINT"; then
        log_error "NVMe is not mounted at $NVME_MOUNT_POINT"
        log_error "Check /etc/fstab and run: sudo mount -a"
        log_error "Or manually mount: sudo mount /dev/nvme0n1p1 $NVME_MOUNT_POINT"
        return 1
    fi
    log_info "NVMe is mounted at $NVME_MOUNT_POINT"
    
    # Show mount details
    mount_info=$(mount | grep "$NVME_MOUNT_POINT")
    log_info "Mount details: $mount_info"
    return 0
}

# Function to check disk space
check_disk_space() {
    # Get disk usage percentage (without % sign)
    usage_pct=$(df -h "$NVME_MOUNT_POINT" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    # Get human-readable sizes
    total_size=$(df -h "$NVME_MOUNT_POINT" | awk 'NR==2 {print $2}')
    used_size=$(df -h "$NVME_MOUNT_POINT" | awk 'NR==2 {print $3}')
    avail_size=$(df -h "$NVME_MOUNT_POINT" | awk 'NR==2 {print $4}')
    
    log_info "Disk usage: $used_size / $total_size ($usage_pct% used, $avail_size available)"
    
    # Check against thresholds
    if [ "$usage_pct" -ge "$CRITICAL_THRESHOLD_PCT" ]; then
        log_error "NVMe disk usage is CRITICAL: ${usage_pct}% (threshold: ${CRITICAL_THRESHOLD_PCT}%)"
        log_error "Free up space immediately or logs may fail to write"
        return 1
    elif [ "$usage_pct" -ge "$WARN_THRESHOLD_PCT" ]; then
        log_warn "NVMe disk usage is HIGH: ${usage_pct}% (threshold: ${WARN_THRESHOLD_PCT}%)"
        log_warn "Consider freeing up space soon"
        return 2
    else
        log_info "NVMe disk space OK: ${usage_pct}% used"
        return 0
    fi
}

# Function to check write permissions
check_write_permissions() {
    test_file="$NVME_MOUNT_POINT/.write_test_$$"
    
    if touch "$test_file" 2>/dev/null; then
        rm -f "$test_file"
        log_info "Write permissions OK on $NVME_MOUNT_POINT"
        return 0
    else
        log_error "Cannot write to $NVME_MOUNT_POINT"
        log_error "Check permissions: ls -ld $NVME_MOUNT_POINT"
        return 1
    fi
}

# Function to check/create required directories
check_directories() {
    local dirs=(
        "$NVME_MOUNT_POINT/suricata/logs"
        "$NVME_MOUNT_POINT/suricata/pcaps"
        "$NVME_MOUNT_POINT/suricata/rules"
        "$NVME_MOUNT_POINT/promtail"
    )
    
    local missing_dirs=()
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [ ${#missing_dirs[@]} -eq 0 ]; then
        log_info "All required directories exist"
        return 0
    else
        log_warn "Missing directories (will be created):"
        for dir in "${missing_dirs[@]}"; do
            echo "  - $dir"
        done
        
        # Check if running in non-interactive mode
        if [ "${AUTO_CREATE_DIRS:-0}" = "1" ]; then
            log_info "AUTO_CREATE_DIRS=1, creating directories automatically"
            for dir in "${missing_dirs[@]}"; do
                sudo mkdir -p "$dir"
                log_info "Created: $dir"
            done
            
            # Set ownership (Suricata typically runs as UID 1000)
            sudo chown -R 1000:1000 "$NVME_MOUNT_POINT/suricata"
            sudo chown -R 1000:1000 "$NVME_MOUNT_POINT/promtail"
            log_info "Set ownership to UID 1000 (Suricata user)"
            return 0
        fi
        
        # Interactive mode: ask user
        read -t 30 -p "Create missing directories? [y/N] " -n 1 -r 2>/dev/null || {
            log_warn "No response after 30 seconds, skipping directory creation"
            return 2
        }
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for dir in "${missing_dirs[@]}"; do
                sudo mkdir -p "$dir"
                log_info "Created: $dir"
            done
            
            # Set ownership (Suricata typically runs as UID 1000)
            sudo chown -R 1000:1000 "$NVME_MOUNT_POINT/suricata"
            sudo chown -R 1000:1000 "$NVME_MOUNT_POINT/promtail"
            log_info "Set ownership to UID 1000 (Suricata user)"
            return 0
        else
            log_warn "Directories not created. Docker containers may fail to start."
            return 2
        fi
    fi
}

# Function to show detailed storage breakdown
show_storage_breakdown() {
    log_info "Storage breakdown by directory:"
    if command -v du &> /dev/null; then
        sudo du -sh "$NVME_MOUNT_POINT"/* 2>/dev/null | sort -h || true
    fi
}

# Main execution
main() {
    echo "================================================"
    echo "Orion Sentinel NetSec Pi - NVMe Health Check"
    echo "================================================"
    echo ""
    
    exit_code=0
    
    # Run all checks
    check_mount_exists || exit_code=1
    
    if [ $exit_code -eq 0 ]; then
        check_is_mounted || exit_code=1
    fi
    
    if [ $exit_code -eq 0 ]; then
        check_disk_space || {
            result=$?
            if [ $result -eq 1 ]; then
                exit_code=1
            elif [ $result -eq 2 ] && [ $exit_code -eq 0 ]; then
                exit_code=2
            fi
        }
    fi
    
    if [ $exit_code -eq 0 ]; then
        check_write_permissions || exit_code=1
    fi
    
    if [ $exit_code -eq 0 ]; then
        check_directories || {
            result=$?
            if [ $result -eq 2 ] && [ $exit_code -eq 0 ]; then
                exit_code=2
            fi
        }
    fi
    
    if [ $exit_code -eq 0 ]; then
        show_storage_breakdown
    fi
    
    echo ""
    echo "================================================"
    
    if [ $exit_code -eq 0 ]; then
        log_info "All checks PASSED ✓"
        echo "NVMe storage is ready for NetSec Pi deployment"
        exit 0
    elif [ $exit_code -eq 2 ]; then
        log_warn "Checks completed with WARNINGS"
        echo "Review warnings above and consider taking action"
        exit 2
    else
        log_error "Critical checks FAILED ✗"
        echo "Fix errors above before starting NetSec Pi services"
        exit 1
    fi
}

# Run main function
main "$@"

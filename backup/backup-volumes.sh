#!/bin/bash
# Orion Sentinel - Volume Backup Script
# Backs up all critical Docker volumes to compressed archives
#
# Usage:
#   sudo ./backup-volumes.sh [backup_dir]
#
# Default backup location: /srv/backups/orion/YYYY-MM-DD_HH-MM-SS

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default backup directory
DEFAULT_BACKUP_DIR="/srv/backups/orion"
BACKUP_DIR="${1:-$DEFAULT_BACKUP_DIR}"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"

# Critical volumes to backup
# Format: volume_name:description
CRITICAL_VOLUMES=(
    "orion-sentinel-netsec-ai_suricata-logs:Suricata IDS logs and alerts"
    "orion-sentinel-netsec-ai_suricata-rules:Suricata rules and configuration"
    "orion-sentinel-netsec-ai_soar-data:SOAR playbook execution history"
    "orion-sentinel-netsec-ai_inventory-data:Device inventory database"
    "orion-sentinel-netsec-ai_change-data:Network change monitoring data"
    "orion-sentinel-netsec-ai_health-data:Security health score data"
)

echo -e "${GREEN}=== Orion Sentinel Volume Backup ===${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo "Backup location: ${BACKUP_PATH}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}" 
   exit 1
fi

# Create backup directory
mkdir -p "${BACKUP_PATH}"
echo -e "${GREEN}✓${NC} Created backup directory: ${BACKUP_PATH}"

# Function to backup a single volume
backup_volume() {
    local volume_spec="$1"
    local volume_name="${volume_spec%%:*}"
    local description="${volume_spec##*:}"
    
    echo ""
    echo -e "${YELLOW}Backing up:${NC} ${volume_name}"
    echo "  Description: ${description}"
    
    # Check if volume exists
    if ! docker volume inspect "${volume_name}" > /dev/null 2>&1; then
        echo -e "${YELLOW}  ⚠ Volume not found - skipping${NC}"
        return 0
    fi
    
    # Get volume mount point
    local volume_path=$(docker volume inspect "${volume_name}" --format '{{ .Mountpoint }}')
    
    # Create tar.gz backup
    local backup_file="${BACKUP_PATH}/${volume_name}.tar.gz"
    
    if tar -czf "${backup_file}" -C "$(dirname "${volume_path}")" "$(basename "${volume_path}")" 2>/dev/null; then
        local size=$(du -h "${backup_file}" | cut -f1)
        echo -e "${GREEN}  ✓ Backed up${NC} (${size}): ${backup_file}"
    else
        echo -e "${RED}  ✗ Backup failed${NC}"
        return 1
    fi
}

# Backup all critical volumes
echo ""
echo "=== Backing up critical volumes ==="
BACKUP_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

for volume_spec in "${CRITICAL_VOLUMES[@]}"; do
    if backup_volume "${volume_spec}"; then
        if docker volume inspect "${volume_spec%%:*}" > /dev/null 2>&1; then
            ((BACKUP_COUNT++))
        else
            ((SKIP_COUNT++))
        fi
    else
        ((FAIL_COUNT++))
    fi
done

# Create backup manifest
MANIFEST="${BACKUP_PATH}/backup-manifest.txt"
cat > "${MANIFEST}" << EOF
Orion Sentinel Backup Manifest
================================
Backup Date: $(date)
Hostname: $(hostname)
Backup Path: ${BACKUP_PATH}

Volumes Backed Up:
EOF

for volume_spec in "${CRITICAL_VOLUMES[@]}"; do
    volume_name="${volume_spec%%:*}"
    description="${volume_spec##*:}"
    if [ -f "${BACKUP_PATH}/${volume_name}.tar.gz" ]; then
        size=$(du -h "${BACKUP_PATH}/${volume_name}.tar.gz" | cut -f1)
        echo "  - ${volume_name} (${size}) - ${description}" >> "${MANIFEST}"
    fi
done

cat >> "${MANIFEST}" << EOF

Backup Statistics:
  - Successful: ${BACKUP_COUNT}
  - Skipped (not found): ${SKIP_COUNT}
  - Failed: ${FAIL_COUNT}

Restore Instructions:
  Use ./backup/restore-volume.sh to restore individual volumes.
  Example: sudo ./backup/restore-volume.sh ${BACKUP_PATH}/VOLUME_NAME.tar.gz
EOF

echo ""
echo -e "${GREEN}=== Backup Summary ===${NC}"
echo "  Successful: ${BACKUP_COUNT}"
echo "  Skipped: ${SKIP_COUNT}"
echo "  Failed: ${FAIL_COUNT}"
echo ""
echo "Backup manifest: ${MANIFEST}"
echo ""

if [ ${FAIL_COUNT} -gt 0 ]; then
    echo -e "${RED}⚠ Some backups failed. Check the output above.${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Backup completed successfully!${NC}"
    
    # Calculate total backup size
    TOTAL_SIZE=$(du -sh "${BACKUP_PATH}" | cut -f1)
    echo "Total backup size: ${TOTAL_SIZE}"
    
    # Show retention recommendations
    echo ""
    echo "Retention recommendations:"
    echo "  - Keep daily backups for 7 days"
    echo "  - Keep weekly backups for 4 weeks"
    echo "  - Keep monthly backups for 6 months"
    echo ""
    echo "To automate weekly backups, add to crontab:"
    echo "  0 2 * * 0 $(realpath "$0") ${BACKUP_DIR}"
fi

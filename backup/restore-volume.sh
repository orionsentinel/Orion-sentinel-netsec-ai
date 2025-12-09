#!/bin/bash
# Orion Sentinel - Volume Restore Script
# Restores Docker volumes from backup archives
#
# Usage:
#   sudo ./restore-volume.sh <backup_file.tar.gz> [volume_name]
#
# Examples:
#   # Restore with automatic volume name detection
#   sudo ./restore-volume.sh /srv/backups/orion/2024-01-15_10-30-00/orion-sentinel-netsec-ai_inventory-data.tar.gz
#
#   # Restore to a different volume name
#   sudo ./restore-volume.sh /srv/backups/orion/2024-01-15_10-30-00/orion-sentinel-netsec-ai_inventory-data.tar.gz my-custom-volume

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}" 
   exit 1
fi

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}ERROR: Missing backup file argument${NC}"
    echo ""
    echo "Usage: $0 <backup_file.tar.gz> [volume_name]"
    echo ""
    echo "Examples:"
    echo "  $0 /srv/backups/orion/2024-01-15/orion-sentinel-netsec-ai_inventory-data.tar.gz"
    echo "  $0 backup.tar.gz my-custom-volume-name"
    exit 1
fi

BACKUP_FILE="$1"
VOLUME_NAME="${2:-}"

# Validate backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}ERROR: Backup file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

# Extract volume name from filename if not provided
if [ -z "${VOLUME_NAME}" ]; then
    VOLUME_NAME=$(basename "${BACKUP_FILE}" .tar.gz)
    echo -e "${BLUE}Auto-detected volume name:${NC} ${VOLUME_NAME}"
fi

echo -e "${GREEN}=== Orion Sentinel Volume Restore ===${NC}"
echo "Backup file: ${BACKUP_FILE}"
echo "Target volume: ${VOLUME_NAME}"
echo ""

# Check if volume already exists
if docker volume inspect "${VOLUME_NAME}" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Warning: Volume '${VOLUME_NAME}' already exists${NC}"
    echo ""
    echo "This will OVERWRITE the existing volume data!"
    echo "Make sure you have stopped all containers using this volume."
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Restore cancelled."
        exit 0
    fi
    
    # Check if any containers are using this volume
    CONTAINERS_USING=$(docker ps -a --filter volume="${VOLUME_NAME}" --format "{{.Names}}" | tr '\n' ', ' | sed 's/,$//')
    if [ -n "${CONTAINERS_USING}" ]; then
        echo -e "${YELLOW}⚠ Warning: The following containers are using this volume:${NC}"
        echo "  ${CONTAINERS_USING}"
        echo ""
        echo "You should stop these containers before restoring:"
        echo "  docker compose --profile netsec-core --profile ai down"
        echo ""
        read -p "Continue anyway? (yes/no): " -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Restore cancelled."
            exit 0
        fi
    fi
else
    echo "Creating new volume: ${VOLUME_NAME}"
    docker volume create "${VOLUME_NAME}"
fi

# Get volume mount point
VOLUME_PATH=$(docker volume inspect "${VOLUME_NAME}" --format '{{ .Mountpoint }}')
echo "Volume mount point: ${VOLUME_PATH}"
echo ""

# Clear existing volume data
echo -e "${YELLOW}Clearing existing volume data...${NC}"
# Safety check: Ensure VOLUME_PATH is not empty and looks like a Docker volume path
if [ -z "${VOLUME_PATH}" ]; then
    echo -e "${RED}ERROR: Volume path is empty - aborting for safety${NC}"
    exit 1
fi
if [[ ! "${VOLUME_PATH}" =~ ^/var/lib/docker/volumes/ ]]; then
    echo -e "${RED}ERROR: Volume path doesn't look like a Docker volume - aborting for safety${NC}"
    echo "Expected path starting with /var/lib/docker/volumes/, got: ${VOLUME_PATH}"
    exit 1
fi
rm -rf "${VOLUME_PATH:?}"/*
echo -e "${GREEN}✓${NC} Existing data cleared"

# Extract backup to volume
echo ""
echo -e "${YELLOW}Restoring backup...${NC}"
TEMP_DIR=$(mktemp -d)

if tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"; then
    # Find the extracted directory (should be _data or similar)
    EXTRACTED_DIR=$(find "${TEMP_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    
    if [ -z "${EXTRACTED_DIR}" ]; then
        echo -e "${RED}ERROR: No directory found in backup archive${NC}"
        rm -rf "${TEMP_DIR}"
        exit 1
    fi
    
    # Copy contents to volume
    cp -a "${EXTRACTED_DIR}"/* "${VOLUME_PATH}/" 2>&1 | tee /tmp/restore-errors.log || {
        # Check if errors were due to empty directory (acceptable) or real issues
        if [ ! -s /tmp/restore-errors.log ]; then
            # No output means success
            true
        elif grep -q "No such file or directory" /tmp/restore-errors.log; then
            echo -e "${YELLOW}⚠ Warning: Some files could not be restored - check logs${NC}"
            cat /tmp/restore-errors.log
        else
            echo -e "${RED}ERROR: Failed to copy backup contents${NC}"
            cat /tmp/restore-errors.log
            rm -f /tmp/restore-errors.log
            rm -rf "${TEMP_DIR}"
            exit 1
        fi
    }
    rm -f /tmp/restore-errors.log
    
    # Calculate restored size
    RESTORED_SIZE=$(du -sh "${VOLUME_PATH}" | cut -f1)
    
    echo -e "${GREEN}✓ Restore completed${NC}"
    echo "Restored size: ${RESTORED_SIZE}"
    
    # Cleanup
    rm -rf "${TEMP_DIR}"
else
    echo -e "${RED}ERROR: Failed to extract backup archive${NC}"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Restore Summary ===${NC}"
echo "  Volume: ${VOLUME_NAME}"
echo "  Size: ${RESTORED_SIZE}"
echo "  Source: ${BACKUP_FILE}"
echo ""
echo -e "${GREEN}✓ Volume restored successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify the restored data is correct"
echo "  2. Restart services that use this volume:"
echo "     make restart"
echo ""

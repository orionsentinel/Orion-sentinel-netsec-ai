#!/usr/bin/env bash
# Orion Sentinel Restore Script
# Restores inventory, configs, and state from a backup directory

set -euo pipefail

# Determine repo root (script location parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "======================================"
echo "Orion Sentinel - Restore All"
echo "======================================"
echo ""

# Check if backup directory provided
if [ $# -eq 0 ]; then
    echo "Error: No backup directory specified"
    echo ""
    echo "Usage: $0 <backup-directory>"
    echo ""
    echo "Available backups:"
    if [ -d "${REPO_ROOT}/backups" ]; then
        ls -1dt "${REPO_ROOT}/backups/backup_"* 2>/dev/null || echo "  (none found)"
    else
        echo "  (no backups directory found)"
    fi
    echo ""
    exit 1
fi

BACKUP_DIR="$1"

# Validate backup directory
if [ ! -d "${BACKUP_DIR}" ]; then
    echo "Error: Backup directory not found: ${BACKUP_DIR}"
    exit 1
fi

if [ ! -f "${BACKUP_DIR}/backup_manifest.txt" ]; then
    echo "Warning: Backup manifest not found. This may not be a valid backup."
    echo ""
fi

echo "Repository Root: ${REPO_ROOT}"
echo "Backup Source: ${BACKUP_DIR}"
echo ""

# Display backup info if manifest exists
if [ -f "${BACKUP_DIR}/backup_manifest.txt" ]; then
    echo "Backup Information:"
    echo "-------------------"
    head -10 "${BACKUP_DIR}/backup_manifest.txt"
    echo ""
fi

# Show what will be restored
echo "Files to restore:"
echo "-----------------"
find "${BACKUP_DIR}" -type f -not -name "backup_manifest.txt" -not -name "git_*.txt" -not -name "ai_models_manifest.txt" | sed "s|${BACKUP_DIR}/||" | sort
echo ""

# Confirmation prompt
read -p "Continue with restore? This will overwrite existing files. (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."
echo ""

# Function to restore a file or directory if it exists in backup
restore_if_exists() {
    local src="$1"
    local dst="$2"
    local description="$3"
    
    if [ -e "${src}" ]; then
        echo "✓ Restoring: ${description}"
        mkdir -p "$(dirname "${dst}")"
        cp -r "${src}" "${dst}"
    else
        echo "⊘ Skipped (not in backup): ${description}"
    fi
}

# 1. Restore data directory (inventory, state files)
echo "[1/5] Device Inventory & State Files"
restore_if_exists "${BACKUP_DIR}/data" "${REPO_ROOT}/data" "Data directory"
restore_if_exists "${BACKUP_DIR}/var" "${REPO_ROOT}/var" "Var directory"
echo ""

# 2. Restore configuration files
echo "[2/5] Configuration Files"
restore_if_exists "${BACKUP_DIR}/config" "${REPO_ROOT}/config" "Config directory"
restore_if_exists "${BACKUP_DIR}/.env" "${REPO_ROOT}/.env" "Root .env file"
restore_if_exists "${BACKUP_DIR}/stacks/nsm/.env" "${REPO_ROOT}/stacks/nsm/.env" "NSM stack .env"
restore_if_exists "${BACKUP_DIR}/stacks/ai/.env" "${REPO_ROOT}/stacks/ai/.env" "AI stack .env"
echo ""

# 3. Restore Grafana configuration
echo "[3/5] Grafana Configuration"
restore_if_exists "${BACKUP_DIR}/stacks/nsm/grafana" "${REPO_ROOT}/stacks/nsm/grafana" "Grafana configs"
restore_if_exists "${BACKUP_DIR}/config/grafana" "${REPO_ROOT}/config/grafana" "Grafana dashboard configs"
echo ""

# 4. Display git state info
echo "[4/5] Git State Information"
if [ -f "${BACKUP_DIR}/git_commit.txt" ]; then
    echo "Backup was created from commit:"
    cat "${BACKUP_DIR}/git_commit.txt"
    echo ""
    echo "Current repository commit:"
    git -C "${REPO_ROOT}" --no-pager log -1 --pretty=format:"%H%n%ai%n%s" 2>/dev/null || echo "Unable to determine"
    echo ""
    echo ""
    echo "Note: Git state is informational only. Run 'git checkout <commit>' manually if needed."
else
    echo "⊘ No git state information in backup"
fi
echo ""

# 5. Display AI models manifest
echo "[5/5] AI Models Information"
if [ -f "${BACKUP_DIR}/ai_models_manifest.txt" ]; then
    echo "AI models in backup (manifest only, not restored):"
    cat "${BACKUP_DIR}/ai_models_manifest.txt"
    echo ""
    echo "TODO: AI model files are large and not automatically restored."
    echo "      Manually copy them from your model storage if needed."
else
    echo "⊘ No AI models manifest in backup"
fi
echo ""

# TODO: Advanced restore components
echo "======================================"
echo "Advanced Components (TODO)"
echo "======================================"
echo ""
echo "The following components require manual restore procedures:"
echo ""
echo "• Loki Data: Time-series log data in /var/lib/docker/volumes/"
echo "  - Stop Loki container: docker compose -f stacks/nsm/docker-compose.yml stop loki"
echo "  - Copy data from backup volume storage if available"
echo "  - Restart: docker compose -f stacks/nsm/docker-compose.yml start loki"
echo ""
echo "• Grafana Dashboards: May need to be re-imported via UI"
echo "  - Access Grafana at http://localhost:3000"
echo "  - Go to Dashboards → Import"
echo ""
echo "• Docker Volumes: Use 'docker volume' commands for persistent data"
echo "  - List: docker volume ls"
echo "  - Inspect: docker volume inspect <volume-name>"
echo ""

echo "======================================"
echo "Restore Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Review restored configuration files"
echo "2. Update any environment-specific settings (.env files)"
echo "3. Restart services: cd stacks/nsm && docker compose up -d"
echo "4. Verify services: docker compose ps"
echo ""

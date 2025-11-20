#!/usr/bin/env bash
# Orion Sentinel Backup Script
# Creates timestamped backups of inventory, configs, and state files

set -euo pipefail

# Determine repo root (script location parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Backup destination
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${REPO_ROOT}/backups/backup_${TIMESTAMP}"

echo "======================================"
echo "Orion Sentinel - Backup All"
echo "======================================"
echo ""
echo "Repository Root: ${REPO_ROOT}"
echo "Backup Directory: ${BACKUP_DIR}"
echo ""

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Function to backup a file or directory if it exists
backup_if_exists() {
    local src="$1"
    local dst="$2"
    local description="$3"
    
    if [ -e "${src}" ]; then
        echo "✓ Backing up: ${description}"
        mkdir -p "$(dirname "${dst}")"
        cp -r "${src}" "${dst}"
    else
        echo "⊘ Skipped (not found): ${description}"
    fi
}

echo "Starting backup..."
echo ""

# 1. Backup inventory database(s)
echo "[1/7] Device Inventory & State Files"
backup_if_exists "${REPO_ROOT}/data/inventory.db" "${BACKUP_DIR}/data/inventory.db" "Inventory database"
backup_if_exists "${REPO_ROOT}/data" "${BACKUP_DIR}/data" "Data directory"
backup_if_exists "${REPO_ROOT}/var" "${BACKUP_DIR}/var" "Var directory"
echo ""

# 2. Backup configuration files
echo "[2/7] Configuration Files"
backup_if_exists "${REPO_ROOT}/config" "${BACKUP_DIR}/config" "Config directory"
backup_if_exists "${REPO_ROOT}/.env" "${BACKUP_DIR}/.env" "Root .env file"
backup_if_exists "${REPO_ROOT}/stacks/nsm/.env" "${BACKUP_DIR}/stacks/nsm/.env" "NSM stack .env"
backup_if_exists "${REPO_ROOT}/stacks/ai/.env" "${BACKUP_DIR}/stacks/ai/.env" "AI stack .env"
echo ""

# 3. Backup playbooks
echo "[3/7] SOAR Playbooks"
backup_if_exists "${REPO_ROOT}/config/playbooks.yml" "${BACKUP_DIR}/config/playbooks.yml" "Playbooks config"
echo ""

# 4. Backup Grafana dashboards and datasources (if customized)
echo "[4/7] Grafana Configuration"
backup_if_exists "${REPO_ROOT}/stacks/nsm/grafana" "${BACKUP_DIR}/stacks/nsm/grafana" "Grafana configs"
backup_if_exists "${REPO_ROOT}/config/grafana" "${BACKUP_DIR}/config/grafana" "Grafana dashboard configs"
echo ""

# 5. AI models manifest (not the models themselves - they're large)
echo "[5/7] AI Models Manifest"
if [ -d "${REPO_ROOT}/stacks/ai/models" ]; then
    echo "✓ Creating AI models manifest"
    find "${REPO_ROOT}/stacks/ai/models" -type f > "${BACKUP_DIR}/ai_models_manifest.txt" 2>/dev/null || true
    ls -lh "${REPO_ROOT}/stacks/ai/models" >> "${BACKUP_DIR}/ai_models_manifest.txt" 2>/dev/null || true
else
    echo "⊘ Skipped (not found): AI models directory"
fi
echo ""

# 6. Git commit hash
echo "[6/7] Git State"
if [ -d "${REPO_ROOT}/.git" ]; then
    echo "✓ Recording git commit hash"
    git -C "${REPO_ROOT}" rev-parse HEAD > "${BACKUP_DIR}/git_commit.txt" 2>/dev/null || echo "unknown" > "${BACKUP_DIR}/git_commit.txt"
    git -C "${REPO_ROOT}" status --short > "${BACKUP_DIR}/git_status.txt" 2>/dev/null || true
    git -C "${REPO_ROOT}" --no-pager log -1 --pretty=format:"%H%n%ai%n%s" >> "${BACKUP_DIR}/git_commit.txt" 2>/dev/null || true
else
    echo "⊘ Not a git repository"
fi
echo ""

# 7. Create backup manifest
echo "[7/7] Backup Manifest"
cat > "${BACKUP_DIR}/backup_manifest.txt" <<EOF
Orion Sentinel Backup
=====================
Timestamp: ${TIMESTAMP}
Date: $(date)
Hostname: $(hostname)
User: $(whoami)
Repository: ${REPO_ROOT}

Backed Up:
EOF

find "${BACKUP_DIR}" -type f | sed "s|${BACKUP_DIR}/||" | sort >> "${BACKUP_DIR}/backup_manifest.txt"

echo "✓ Manifest created"
echo ""

# Summary
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
FILE_COUNT=$(find "${BACKUP_DIR}" -type f | wc -l)

echo "======================================"
echo "Backup Complete!"
echo "======================================"
echo "Location: ${BACKUP_DIR}"
echo "Size: ${BACKUP_SIZE}"
echo "Files: ${FILE_COUNT}"
echo ""
echo "To restore, run:"
echo "  ./scripts/restore-all.sh ${BACKUP_DIR}"
echo ""

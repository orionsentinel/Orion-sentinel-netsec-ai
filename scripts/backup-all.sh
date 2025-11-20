#!/usr/bin/env bash
#
# backup-all.sh
# 
# Backs up Orion Sentinel NSM AI configuration, state files, and metadata
# to a timestamped directory under backups/
#
# Usage: ./scripts/backup-all.sh
#

set -euo pipefail

# Determine repo root (script is in scripts/ directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Create timestamped backup directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${REPO_ROOT}/backups/backup_${TIMESTAMP}"

echo "==> Orion Sentinel Backup"
echo "Backup directory: ${BACKUP_DIR}"
echo ""

mkdir -p "${BACKUP_DIR}"

# Backup metadata
echo "[1/6] Backing up metadata..."
{
  echo "Backup created: $(date -Iseconds)"
  echo "Hostname: $(hostname)"
  echo "Git commit: $(cd "${REPO_ROOT}" && git rev-parse HEAD 2>/dev/null || echo 'not-a-git-repo')"
  echo "Git branch: $(cd "${REPO_ROOT}" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
  echo "Git status: $(cd "${REPO_ROOT}" && git status --short 2>/dev/null || echo 'not-a-git-repo')"
} > "${BACKUP_DIR}/metadata.txt"
echo "   ✓ Created metadata.txt"

# Backup config files
echo "[2/6] Backing up configuration files..."
mkdir -p "${BACKUP_DIR}/config"

# Main config directory
if [ -d "${REPO_ROOT}/config" ]; then
  cp -r "${REPO_ROOT}/config"/* "${BACKUP_DIR}/config/" 2>/dev/null || true
  echo "   ✓ Backed up config/"
fi

# Stack configs (NSM)
if [ -d "${REPO_ROOT}/stacks/nsm" ]; then
  mkdir -p "${BACKUP_DIR}/stacks/nsm"
  cp "${REPO_ROOT}/stacks/nsm/.env" "${BACKUP_DIR}/stacks/nsm/" 2>/dev/null || echo "   ⚠ No stacks/nsm/.env found"
  cp -r "${REPO_ROOT}/stacks/nsm/suricata" "${BACKUP_DIR}/stacks/nsm/" 2>/dev/null || true
  cp -r "${REPO_ROOT}/stacks/nsm/promtail" "${BACKUP_DIR}/stacks/nsm/" 2>/dev/null || true
  cp -r "${REPO_ROOT}/stacks/nsm/loki" "${BACKUP_DIR}/stacks/nsm/" 2>/dev/null || true
  cp -r "${REPO_ROOT}/stacks/nsm/grafana" "${BACKUP_DIR}/stacks/nsm/" 2>/dev/null || true
  echo "   ✓ Backed up NSM stack configs"
fi

# Stack configs (AI)
if [ -d "${REPO_ROOT}/stacks/ai" ]; then
  mkdir -p "${BACKUP_DIR}/stacks/ai"
  cp "${REPO_ROOT}/stacks/ai/.env" "${BACKUP_DIR}/stacks/ai/" 2>/dev/null || echo "   ⚠ No stacks/ai/.env found"
  cp -r "${REPO_ROOT}/stacks/ai/config" "${BACKUP_DIR}/stacks/ai/" 2>/dev/null || true
  echo "   ✓ Backed up AI stack configs"
fi

# Root .env files
cp "${REPO_ROOT}/.env" "${BACKUP_DIR}/" 2>/dev/null || echo "   ⚠ No root .env found"

# Backup inventory and state files
echo "[3/6] Backing up state and inventory files..."
mkdir -p "${BACKUP_DIR}/data"

# Look for SQLite databases in common locations
for db_path in \
  "${REPO_ROOT}/data/inventory.db" \
  "${REPO_ROOT}/var/inventory.db" \
  "${REPO_ROOT}/stacks/ai/data/inventory.db" \
  "${REPO_ROOT}/stacks/ai/var/inventory.db"; do
  
  if [ -f "${db_path}" ]; then
    rel_path="${db_path#${REPO_ROOT}/}"
    target_dir="${BACKUP_DIR}/$(dirname "${rel_path}")"
    mkdir -p "${target_dir}"
    cp "${db_path}" "${target_dir}/"
    echo "   ✓ Backed up ${rel_path}"
  fi
done

# Look for JSON state files
for json_path in \
  "${REPO_ROOT}/data"/*.json \
  "${REPO_ROOT}/var"/*.json \
  "${REPO_ROOT}/stacks/ai/data"/*.json \
  "${REPO_ROOT}/stacks/ai/var"/*.json; do
  
  if [ -f "${json_path}" ]; then
    rel_path="${json_path#${REPO_ROOT}/}"
    target_dir="${BACKUP_DIR}/$(dirname "${rel_path}")"
    mkdir -p "${target_dir}"
    cp "${json_path}" "${target_dir}/"
    echo "   ✓ Backed up ${rel_path}"
  fi
done

# Backup threat intel cache if present
if [ -d "${REPO_ROOT}/stacks/ai/var/threat_intel_cache" ]; then
  mkdir -p "${BACKUP_DIR}/stacks/ai/var"
  cp -r "${REPO_ROOT}/stacks/ai/var/threat_intel_cache" "${BACKUP_DIR}/stacks/ai/var/" 2>/dev/null || true
  echo "   ✓ Backed up threat intel cache"
fi

# Backup AI models manifest (not the models themselves)
echo "[4/6] Creating AI models manifest..."
if [ -d "${REPO_ROOT}/stacks/ai/models" ]; then
  {
    echo "AI Models Directory Manifest"
    echo "============================="
    echo ""
    echo "NOTE: Model files (.onnx, .tflite, .pb, .h5) are NOT backed up due to size."
    echo "      Users should download models separately as documented."
    echo ""
    echo "Contents of stacks/ai/models/:"
    ls -lh "${REPO_ROOT}/stacks/ai/models/" 2>/dev/null || echo "Directory empty or not accessible"
  } > "${BACKUP_DIR}/models_manifest.txt"
  echo "   ✓ Created models_manifest.txt"
else
  echo "   ⚠ No models directory found"
fi

# Backup playbooks
echo "[5/6] Backing up playbooks..."
if [ -f "${REPO_ROOT}/stacks/ai/config/playbooks.yml" ]; then
  mkdir -p "${BACKUP_DIR}/stacks/ai/config"
  cp "${REPO_ROOT}/stacks/ai/config/playbooks.yml" "${BACKUP_DIR}/stacks/ai/config/"
  echo "   ✓ Backed up playbooks.yml"
elif [ -f "${REPO_ROOT}/config/playbooks.yml" ]; then
  cp "${REPO_ROOT}/config/playbooks.yml" "${BACKUP_DIR}/config/"
  echo "   ✓ Backed up playbooks.yml"
else
  echo "   ⚠ No playbooks.yml found"
fi

# Create backup summary
echo "[6/6] Creating backup summary..."
{
  echo "Orion Sentinel Backup Summary"
  echo "=============================="
  echo ""
  echo "Backup timestamp: ${TIMESTAMP}"
  echo "Backup location: ${BACKUP_DIR}"
  echo ""
  echo "Backed up items:"
  echo "  - Metadata and git info"
  echo "  - Configuration files (config/, .env)"
  echo "  - NSM stack configs (suricata, loki, promtail, grafana)"
  echo "  - AI stack configs (playbooks, service configs)"
  echo "  - Inventory databases (*.db)"
  echo "  - State files (*.json)"
  echo "  - Threat intel cache (if present)"
  echo "  - AI models manifest (listing only)"
  echo ""
  echo "Backup size:"
  du -sh "${BACKUP_DIR}" || echo "  Could not determine size"
  echo ""
  echo "To restore this backup:"
  echo "  ./scripts/restore-all.sh ${BACKUP_DIR}"
} > "${BACKUP_DIR}/BACKUP_SUMMARY.txt"

cat "${BACKUP_DIR}/BACKUP_SUMMARY.txt"
echo ""
echo "==> Backup completed successfully!"
echo "Backup location: ${BACKUP_DIR}"

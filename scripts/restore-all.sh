#!/usr/bin/env bash
#
# restore-all.sh
#
# Restores Orion Sentinel NSM AI configuration and state from a backup directory
#
# Usage: ./scripts/restore-all.sh <backup_directory>
#

set -euo pipefail

# Check arguments
if [ $# -ne 1 ]; then
  echo "Usage: $0 <backup_directory>"
  echo ""
  echo "Example: $0 backups/backup_20250120_143022"
  exit 1
fi

BACKUP_DIR="$1"

# Validate backup directory
if [ ! -d "${BACKUP_DIR}" ]; then
  echo "Error: Backup directory not found: ${BACKUP_DIR}"
  exit 1
fi

if [ ! -f "${BACKUP_DIR}/metadata.txt" ]; then
  echo "Warning: This doesn't look like a valid backup (metadata.txt missing)"
  echo "Continue anyway? (y/N)"
  read -r response
  if [[ ! "${response}" =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
  fi
fi

# Determine repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==> Orion Sentinel Restore"
echo "Backup directory: ${BACKUP_DIR}"
echo "Target directory: ${REPO_ROOT}"
echo ""

# Show backup info
if [ -f "${BACKUP_DIR}/BACKUP_SUMMARY.txt" ]; then
  cat "${BACKUP_DIR}/BACKUP_SUMMARY.txt"
  echo ""
fi

if [ -f "${BACKUP_DIR}/metadata.txt" ]; then
  echo "Backup metadata:"
  cat "${BACKUP_DIR}/metadata.txt"
  echo ""
fi

# Confirmation prompt
echo "==> This will restore configuration and state files from the backup."
echo "WARNING: This will overwrite existing files!"
echo ""
echo "Continue with restore? (y/N)"
read -r response

if [[ ! "${response}" =~ ^[Yy]$ ]]; then
  echo "Restore cancelled."
  exit 0
fi

echo ""
echo "Starting restore..."
echo ""

# Restore config files
echo "[1/5] Restoring configuration files..."
if [ -d "${BACKUP_DIR}/config" ]; then
  mkdir -p "${REPO_ROOT}/config"
  cp -r "${BACKUP_DIR}/config"/* "${REPO_ROOT}/config/" 2>/dev/null || true
  echo "   ✓ Restored config/"
fi

# Restore NSM stack configs
if [ -d "${BACKUP_DIR}/stacks/nsm" ]; then
  mkdir -p "${REPO_ROOT}/stacks/nsm"
  
  # Restore .env if present
  if [ -f "${BACKUP_DIR}/stacks/nsm/.env" ]; then
    cp "${BACKUP_DIR}/stacks/nsm/.env" "${REPO_ROOT}/stacks/nsm/"
    echo "   ✓ Restored stacks/nsm/.env"
  fi
  
  # Restore config directories
  for subdir in suricata promtail loki grafana; do
    if [ -d "${BACKUP_DIR}/stacks/nsm/${subdir}" ]; then
      cp -r "${BACKUP_DIR}/stacks/nsm/${subdir}" "${REPO_ROOT}/stacks/nsm/" 2>/dev/null || true
      echo "   ✓ Restored stacks/nsm/${subdir}"
    fi
  done
fi

# Restore AI stack configs
if [ -d "${BACKUP_DIR}/stacks/ai" ]; then
  mkdir -p "${REPO_ROOT}/stacks/ai"
  
  # Restore .env if present
  if [ -f "${BACKUP_DIR}/stacks/ai/.env" ]; then
    cp "${BACKUP_DIR}/stacks/ai/.env" "${REPO_ROOT}/stacks/ai/"
    echo "   ✓ Restored stacks/ai/.env"
  fi
  
  # Restore config directory
  if [ -d "${BACKUP_DIR}/stacks/ai/config" ]; then
    cp -r "${BACKUP_DIR}/stacks/ai/config" "${REPO_ROOT}/stacks/ai/" 2>/dev/null || true
    echo "   ✓ Restored stacks/ai/config"
  fi
fi

# Restore root .env
if [ -f "${BACKUP_DIR}/.env" ]; then
  cp "${BACKUP_DIR}/.env" "${REPO_ROOT}/"
  echo "   ✓ Restored root .env"
fi

# Restore state and inventory files
echo "[2/5] Restoring state and inventory files..."
if [ -d "${BACKUP_DIR}/data" ]; then
  mkdir -p "${REPO_ROOT}/data"
  cp -r "${BACKUP_DIR}/data"/* "${REPO_ROOT}/data/" 2>/dev/null || true
  echo "   ✓ Restored data/"
fi

if [ -d "${BACKUP_DIR}/var" ]; then
  mkdir -p "${REPO_ROOT}/var"
  cp -r "${BACKUP_DIR}/var"/* "${REPO_ROOT}/var/" 2>/dev/null || true
  echo "   ✓ Restored var/"
fi

# Restore AI stack data if present
if [ -d "${BACKUP_DIR}/stacks/ai/data" ]; then
  mkdir -p "${REPO_ROOT}/stacks/ai/data"
  cp -r "${BACKUP_DIR}/stacks/ai/data"/* "${REPO_ROOT}/stacks/ai/data/" 2>/dev/null || true
  echo "   ✓ Restored stacks/ai/data/"
fi

if [ -d "${BACKUP_DIR}/stacks/ai/var" ]; then
  mkdir -p "${REPO_ROOT}/stacks/ai/var"
  cp -r "${BACKUP_DIR}/stacks/ai/var"/* "${REPO_ROOT}/stacks/ai/var/" 2>/dev/null || true
  echo "   ✓ Restored stacks/ai/var/"
fi

# Note about Loki data
echo "[3/5] Checking for Loki data..."
echo "   ⚠ NOTE: Loki data is not backed up by default (large volume)"
echo "   TODO: For production, implement Loki backup/restore separately"
echo "         Options: Loki object storage, volume snapshots, or export queries"

# Note about models
echo "[4/5] Checking for AI models..."
if [ -f "${BACKUP_DIR}/models_manifest.txt" ]; then
  cat "${BACKUP_DIR}/models_manifest.txt"
  echo ""
  echo "   ⚠ AI models are NOT restored from backup (too large)"
  echo "   Please download models separately as documented"
else
  echo "   ⚠ No models manifest found in backup"
fi

# Set permissions
echo "[5/5] Setting permissions..."
# Ensure .env files are not world-readable
find "${REPO_ROOT}" -name ".env" -type f -exec chmod 600 {} \; 2>/dev/null || true
echo "   ✓ Set restrictive permissions on .env files"

# Create restore log
RESTORE_LOG="${REPO_ROOT}/backups/restore_$(date +%Y%m%d_%H%M%S).log"
{
  echo "Restore completed: $(date -Iseconds)"
  echo "From backup: ${BACKUP_DIR}"
  echo "To directory: ${REPO_ROOT}"
  echo "Hostname: $(hostname)"
} > "${RESTORE_LOG}"

echo ""
echo "==> Restore completed successfully!"
echo "Restore log: ${RESTORE_LOG}"
echo ""
echo "Next steps:"
echo "  1. Review restored files"
echo "  2. Update any environment-specific configurations"
echo "  3. Restart services if needed:"
echo "     cd stacks/nsm && docker compose restart"
echo "     cd stacks/ai && docker compose restart"

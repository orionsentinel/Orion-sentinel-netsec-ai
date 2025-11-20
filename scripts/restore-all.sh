#!/usr/bin/env bash
#
# restore-all.sh - Restore Orion Sentinel NSM+AI system from backup
#
# This script restores configuration, databases, and state files from a backup
# created by backup-all.sh.
#
# Usage: ./scripts/restore-all.sh <backup-directory>
#
# Example: ./scripts/restore-all.sh backups/backup-20241120-143022
#

set -euo pipefail

# Determine repository root (script is in scripts/ subdirectory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Check if backup directory was provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup-directory>"
    echo ""
    echo "Example: $0 backups/backup-20241120-143022"
    echo ""
    echo "Available backups:"
    if [ -d "${REPO_ROOT}/backups" ]; then
        ls -1dt "${REPO_ROOT}"/backups/backup-* 2>/dev/null | head -5 || echo "  No backups found"
    else
        echo "  No backups directory found"
    fi
    exit 1
fi

BACKUP_DIR="$1"

# Convert to absolute path if relative
if [[ "$BACKUP_DIR" != /* ]]; then
    BACKUP_DIR="${REPO_ROOT}/${BACKUP_DIR}"
fi

# Verify backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Verify it's a valid backup
if [ ! -f "$BACKUP_DIR/BACKUP-SUMMARY.txt" ]; then
    echo "Error: Not a valid backup directory (missing BACKUP-SUMMARY.txt)"
    exit 1
fi

# Change to repo root for all operations
cd "${REPO_ROOT}"

echo "==============================================="
echo "Orion Sentinel Restore Script"
echo "==============================================="
echo "Repository: ${REPO_ROOT}"
echo "Restore from: ${BACKUP_DIR}"
echo ""

# Show backup summary
if [ -f "$BACKUP_DIR/BACKUP-SUMMARY.txt" ]; then
    echo "Backup Summary:"
    echo "---------------"
    cat "$BACKUP_DIR/BACKUP-SUMMARY.txt"
    echo ""
fi

# Show what will be restored
echo "Files to be restored:"
echo "---------------------"
if [ -f "$BACKUP_DIR/backup-manifest.txt" ]; then
    grep "✓" "$BACKUP_DIR/backup-manifest.txt" | head -20
    total_files=$(grep -c "✓" "$BACKUP_DIR/backup-manifest.txt" || echo "0")
    if [ "$total_files" -gt 20 ]; then
        echo "  ... and $((total_files - 20)) more files"
    fi
else
    echo "Warning: No manifest found, will restore all files in backup"
fi

echo ""
echo "WARNING: This will overwrite existing configuration and data files!"
echo ""

# Ask for confirmation
read -p "Continue with restore? (yes/N): " confirmation
if [ "$confirmation" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."

# Counter for restored files
RESTORED_COUNT=0

# Restore configuration files
echo "[1/4] Restoring configuration files..."
if [ -d "$BACKUP_DIR/config" ]; then
    mkdir -p config
    cp -r "$BACKUP_DIR/config"/* config/ 2>/dev/null && {
        file_count=$(find "$BACKUP_DIR/config" -type f | wc -l)
        echo "  ✓ Restored ${file_count} config files"
        RESTORED_COUNT=$((RESTORED_COUNT + file_count))
    } || echo "  ⚠ No config files to restore"
else
    echo "  ⚠ No config directory in backup"
fi

# Restore databases and state files
echo "[2/4] Restoring databases and state files..."
if [ -d "$BACKUP_DIR/data" ]; then
    mkdir -p data
    cp -r "$BACKUP_DIR/data"/* data/ 2>/dev/null && {
        file_count=$(find "$BACKUP_DIR/data" -type f | wc -l)
        echo "  ✓ Restored ${file_count} data files"
        RESTORED_COUNT=$((RESTORED_COUNT + file_count))
    } || echo "  ⚠ No data files to restore"
else
    echo "  ⚠ No data directory in backup"
fi

# Restore stacks data (if present)
if [ -d "$BACKUP_DIR/stacks" ]; then
    for stack_dir in "$BACKUP_DIR/stacks"/*; do
        if [ -d "$stack_dir/data" ]; then
            stack_name=$(basename "$stack_dir")
            target_dir="stacks/${stack_name}/data"
            mkdir -p "$target_dir"
            cp -r "$stack_dir/data"/* "$target_dir/" 2>/dev/null && {
                file_count=$(find "$stack_dir/data" -type f | wc -l)
                echo "  ✓ Restored ${file_count} files to ${target_dir}"
                RESTORED_COUNT=$((RESTORED_COUNT + file_count))
            } || echo "  ⚠ No data files in ${stack_name}"
        fi
    done
fi

# Restore environment examples
echo "[3/4] Restoring environment examples..."
for env_file in "$BACKUP_DIR"/.env.example "$BACKUP_DIR"/stacks/*/.env.example; do
    if [ -f "$env_file" ]; then
        relative_path="${env_file#$BACKUP_DIR/}"
        target_path="${relative_path}"
        mkdir -p "$(dirname "$target_path")"
        cp "$env_file" "$target_path"
        echo "  ✓ Restored $target_path"
        RESTORED_COUNT=$((RESTORED_COUNT + 1))
    fi
done

# Show git information from backup
echo "[4/4] Git information from backup..."
if [ -f "$BACKUP_DIR/git-commit.txt" ]; then
    echo "  Backup was created from:"
    cat "$BACKUP_DIR/git-commit.txt" | sed 's/^/    /'
    echo ""
    echo "  Current repository state:"
    echo "    Commit: $(git log -1 --pretty=format:%H 2>/dev/null || echo 'N/A')"
    echo "    Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"
else
    echo "  ⚠ No git information in backup"
fi

echo ""
echo "==============================================="
echo "Restore Complete!"
echo "==============================================="
echo "Restored ${RESTORED_COUNT} files from backup"
echo ""
echo "Next Steps:"
echo "-----------"
echo "1. Review restored configuration files in config/"
echo "2. If you have .env files, you'll need to recreate them"
echo "   (they are not backed up for security reasons)"
echo "3. Restart services if they're running:"
echo "   cd stacks/nsm && docker compose restart"
echo "   cd stacks/ai && docker compose restart"
echo ""
echo "TODO: Advanced Restore Items"
echo "----------------------------"
echo "The following are NOT restored by this script:"
echo "- Loki log data (in Docker volumes)"
echo "- Grafana dashboards (auto-provisioned on startup)"
echo "- Docker volumes (use 'docker volume' commands manually)"
echo "- AI model files (re-download if needed, see ai-models-manifest.txt)"
echo ""
echo "For Loki data restore, you would need to:"
echo "  1. Stop Loki container"
echo "  2. Manually restore Docker volume or data directory"
echo "  3. Restart Loki container"
echo ""

exit 0

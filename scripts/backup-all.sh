#!/usr/bin/env bash
#
# backup-all.sh - Backup Orion Sentinel NSM+AI system state and configuration
#
# This script creates a timestamped backup of:
# - Local SQLite databases and JSON state files
# - Configuration files (playbooks, env examples)
# - Git commit information
# - AI models manifest (list only, not the models themselves)
#
# Usage: ./scripts/backup-all.sh
#
# Backups are stored in: backups/backup-YYYYMMDD-HHMMSS/
#

set -euo pipefail

# Determine repository root (script is in scripts/ subdirectory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Change to repo root for all operations
cd "${REPO_ROOT}"

# Create timestamp for backup directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="backups/backup-${TIMESTAMP}"

echo "==============================================="
echo "Orion Sentinel Backup Script"
echo "==============================================="
echo "Repository: ${REPO_ROOT}"
echo "Backup destination: ${BACKUP_DIR}"
echo ""

# Create backup directory structure
mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}/config"
mkdir -p "${BACKUP_DIR}/data"
mkdir -p "${BACKUP_DIR}/state"

# Track what was backed up
BACKUP_MANIFEST="${BACKUP_DIR}/backup-manifest.txt"
echo "Backup created: $(date)" > "${BACKUP_MANIFEST}"
echo "Repository: ${REPO_ROOT}" >> "${BACKUP_MANIFEST}"
echo "" >> "${BACKUP_MANIFEST}"

# Backup Git commit information
echo "[1/6] Backing up git commit information..."
if [ -d .git ]; then
    git log -1 --pretty=format:"Commit: %H%nAuthor: %an%nDate: %ad%nMessage: %s%n" > "${BACKUP_DIR}/git-commit.txt"
    git branch --show-current > "${BACKUP_DIR}/git-branch.txt"
    echo "  ✓ Git info saved" >> "${BACKUP_MANIFEST}"
else
    echo "  ⚠ No .git directory found (not a git repository)"
fi

# Backup configuration files
echo "[2/6] Backing up configuration files..."
CONFIG_COUNT=0

# Backup playbooks
if [ -f config/playbooks.yml ]; then
    cp config/playbooks.yml "${BACKUP_DIR}/config/"
    echo "  ✓ config/playbooks.yml" >> "${BACKUP_MANIFEST}"
    CONFIG_COUNT=$((CONFIG_COUNT + 1))
fi

# Backup other config files
for config_file in config/*.yml config/*.yaml config/*.json; do
    if [ -f "$config_file" ]; then
        cp "$config_file" "${BACKUP_DIR}/config/"
        echo "  ✓ $config_file" >> "${BACKUP_MANIFEST}"
        CONFIG_COUNT=$((CONFIG_COUNT + 1))
    fi
done

# Backup environment examples (not actual .env with secrets)
for env_file in .env.example stacks/*/.env.example; do
    if [ -f "$env_file" ]; then
        mkdir -p "${BACKUP_DIR}/$(dirname "$env_file")"
        cp "$env_file" "${BACKUP_DIR}/$env_file"
        echo "  ✓ $env_file" >> "${BACKUP_MANIFEST}"
        CONFIG_COUNT=$((CONFIG_COUNT + 1))
    fi
done

echo "  Backed up ${CONFIG_COUNT} configuration files"

# Backup SQLite databases and JSON state files
echo "[3/6] Backing up databases and state files..."
DB_COUNT=0

# Look for common data directories
for data_dir in data var stacks/*/data; do
    if [ -d "$data_dir" ]; then
        # Backup SQLite databases
        while IFS= read -r db_file; do
            if [ -f "$db_file" ]; then
                mkdir -p "${BACKUP_DIR}/$(dirname "$db_file")"
                cp "$db_file" "${BACKUP_DIR}/$db_file"
                echo "  ✓ $db_file" >> "${BACKUP_MANIFEST}"
                DB_COUNT=$((DB_COUNT + 1))
            fi
        done < <(find "$data_dir" -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" 2>/dev/null)
        
        # Backup JSON state files
        while IFS= read -r json_file; do
            if [ -f "$json_file" ]; then
                mkdir -p "${BACKUP_DIR}/$(dirname "$json_file")"
                cp "$json_file" "${BACKUP_DIR}/$json_file"
                echo "  ✓ $json_file" >> "${BACKUP_MANIFEST}"
                DB_COUNT=$((DB_COUNT + 1))
            fi
        done < <(find "$data_dir" -name "*.json" 2>/dev/null)
    fi
done

# Check for inventory database (common location)
if [ -f stacks/ai/inventory.db ]; then
    cp stacks/ai/inventory.db "${BACKUP_DIR}/data/"
    echo "  ✓ stacks/ai/inventory.db" >> "${BACKUP_MANIFEST}"
    DB_COUNT=$((DB_COUNT + 1))
fi

echo "  Backed up ${DB_COUNT} database/state files"

# Create AI models manifest (list, not the models themselves)
echo "[4/6] Creating AI models manifest..."
MODELS_MANIFEST="${BACKUP_DIR}/ai-models-manifest.txt"
echo "AI Models Inventory" > "${MODELS_MANIFEST}"
echo "==================" >> "${MODELS_MANIFEST}"
echo "" >> "${MODELS_MANIFEST}"

if [ -d stacks/ai/models ]; then
    echo "Models directory: stacks/ai/models" >> "${MODELS_MANIFEST}"
    echo "" >> "${MODELS_MANIFEST}"
    
    # List model files (but don't copy them due to size)
    find stacks/ai/models -type f 2>/dev/null | while read -r model_file; do
        if [ -f "$model_file" ]; then
            file_size=$(du -h "$model_file" | cut -f1)
            echo "  - $(basename "$model_file") (${file_size})" >> "${MODELS_MANIFEST}"
        fi
    done
    
    # Count models
    model_count=$(find stacks/ai/models -type f 2>/dev/null | wc -l)
    echo "" >> "${MODELS_MANIFEST}"
    echo "Total models: ${model_count}" >> "${MODELS_MANIFEST}"
    echo "Note: Models not included in backup due to size. Redownload if needed." >> "${MODELS_MANIFEST}"
    echo "  ✓ AI models manifest created (${model_count} models listed)"
else
    echo "No models directory found" >> "${MODELS_MANIFEST}"
    echo "  ⚠ No AI models directory found"
fi

# Backup Docker Compose files (for reference)
echo "[5/6] Backing up Docker Compose files..."
COMPOSE_COUNT=0
for compose_file in stacks/*/docker-compose.yml stacks/*/docker-compose.*.yml; do
    if [ -f "$compose_file" ]; then
        mkdir -p "${BACKUP_DIR}/$(dirname "$compose_file")"
        cp "$compose_file" "${BACKUP_DIR}/$compose_file"
        echo "  ✓ $compose_file" >> "${BACKUP_MANIFEST}"
        COMPOSE_COUNT=$((COMPOSE_COUNT + 1))
    fi
done
echo "  Backed up ${COMPOSE_COUNT} Docker Compose files"

# Create backup summary
echo "[6/6] Creating backup summary..."
SUMMARY="${BACKUP_DIR}/BACKUP-SUMMARY.txt"
cat > "${SUMMARY}" << EOF
=======================================================
Orion Sentinel Backup Summary
=======================================================

Backup Date: $(date)
Backup Location: ${BACKUP_DIR}
Repository: ${REPO_ROOT}

Contents:
---------
✓ Git commit information
✓ Configuration files (${CONFIG_COUNT} files)
✓ Databases and state (${DB_COUNT} files)
✓ AI models manifest
✓ Docker Compose files (${COMPOSE_COUNT} files)

What's NOT Backed Up:
---------------------
- AI model files (too large, listed in ai-models-manifest.txt)
- Loki log data (can be regenerated)
- Grafana dashboards (auto-provisioned from code)
- Suricata logs (can be regenerated)
- Docker volumes (use docker volume backup if needed)

Restore Instructions:
--------------------
To restore this backup, run:
  ./scripts/restore-all.sh ${BACKUP_DIR}

For more information, see: docs/operations.md
=======================================================
EOF

echo ""
echo "==============================================="
echo "Backup Complete!"
echo "==============================================="
echo "Backup location: ${BACKUP_DIR}"
echo ""
echo "Summary:"
cat "${SUMMARY}"

exit 0

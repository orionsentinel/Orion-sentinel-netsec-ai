#!/usr/bin/env bash
#
# upgrade.sh - Safely upgrade Orion Sentinel NSM+AI system
#
# This script performs a safe upgrade by:
# 1. Creating a backup of current state
# 2. Pulling latest code from git
# 3. Pulling latest Docker images
# 4. Restarting services with new images
#
# Usage: ./scripts/upgrade.sh [--skip-backup] [--skip-docker]
#
# Options:
#   --skip-backup    Skip the backup step (not recommended)
#   --skip-docker    Skip docker pull/restart (for code-only updates)
#

set -euo pipefail

# Determine repository root (script is in scripts/ subdirectory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Change to repo root for all operations
cd "${REPO_ROOT}"

# Parse command line arguments
SKIP_BACKUP=false
SKIP_DOCKER=false

for arg in "$@"; do
    case $arg in
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--skip-backup] [--skip-docker]"
            exit 1
            ;;
    esac
done

echo "==============================================="
echo "Orion Sentinel Upgrade Script"
echo "==============================================="
echo "Repository: ${REPO_ROOT}"
echo ""

# Environment checks
echo "[Pre-flight Checks]"
echo "-------------------"

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed"
    exit 1
fi
echo "✓ Git is available: $(git --version | head -1)"

# Check if docker is available (if not skipping docker operations)
if [ "$SKIP_DOCKER" = false ]; then
    if ! command -v docker &> /dev/null; then
        echo "Error: docker is not installed"
        exit 1
    fi
    echo "✓ Docker is available: $(docker --version)"
    
    # Check if docker compose is available (v2 plugin or standalone)
    if docker compose version &> /dev/null; then
        echo "✓ Docker Compose is available: $(docker compose version)"
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "✓ Docker Compose is available: $(docker-compose --version)"
        COMPOSE_CMD="docker-compose"
    else
        echo "Error: docker compose is not installed"
        exit 1
    fi
fi

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "Error: Not in a git repository"
    exit 1
fi
echo "✓ Git repository detected"

# Show current state
echo ""
echo "Current State:"
echo "  Branch: $(git branch --show-current)"
echo "  Commit: $(git log -1 --pretty=format:'%h - %s')"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "Warning: You have uncommitted changes:"
    git status --short
    echo ""
    read -p "Continue anyway? (yes/N): " continue_choice
    if [ "$continue_choice" != "yes" ]; then
        echo "Upgrade cancelled."
        exit 0
    fi
fi

# Step 1: Backup
if [ "$SKIP_BACKUP" = false ]; then
    echo ""
    echo "[Step 1/5] Creating backup..."
    echo "------------------------------"
    if [ -x "${SCRIPT_DIR}/backup-all.sh" ]; then
        "${SCRIPT_DIR}/backup-all.sh"
        echo "✓ Backup completed successfully"
    else
        echo "Error: backup-all.sh not found or not executable"
        exit 1
    fi
else
    echo ""
    echo "[Step 1/5] Skipping backup (--skip-backup specified)"
fi

# Step 2: Git pull
echo ""
echo "[Step 2/5] Pulling latest code from git..."
echo "-------------------------------------------"
echo "Fetching updates..."
git fetch origin

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

# Check if there are updates
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")

if [ -z "$REMOTE" ]; then
    echo "Warning: No upstream branch configured"
    echo "Skipping git pull"
elif [ "$LOCAL" = "$REMOTE" ]; then
    echo "✓ Already up to date"
else
    echo "Updates available, pulling..."
    git pull origin "$CURRENT_BRANCH"
    echo "✓ Code updated successfully"
    echo "  New commit: $(git log -1 --pretty=format:'%h - %s')"
fi

# Step 3: Update Python dependencies
echo ""
echo "[Step 3/5] Checking Python dependencies..."
echo "-------------------------------------------"
if [ -f requirements.txt ]; then
    if command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
        PIP_CMD=$(command -v pip3 || command -v pip)
        echo "Consider running: $PIP_CMD install -r requirements.txt"
        echo "  (Skipping automatic install to avoid system changes)"
    fi
else
    echo "✓ No requirements.txt changes to apply"
fi

# Step 4: Pull Docker images
if [ "$SKIP_DOCKER" = false ]; then
    echo ""
    echo "[Step 4/5] Pulling latest Docker images..."
    echo "-------------------------------------------"
    
    # Pull NSM stack images
    if [ -f stacks/nsm/docker-compose.yml ]; then
        echo "Pulling NSM stack images..."
        cd stacks/nsm
        $COMPOSE_CMD pull || echo "Warning: Some images could not be pulled (this is OK if using local builds)"
        cd "${REPO_ROOT}"
        echo "✓ NSM stack images updated"
    fi
    
    # Pull AI stack images
    if [ -f stacks/ai/docker-compose.yml ]; then
        echo "Pulling AI stack images..."
        cd stacks/ai
        $COMPOSE_CMD pull || echo "Warning: Some images could not be pulled (this is OK if using local builds)"
        cd "${REPO_ROOT}"
        echo "✓ AI stack images updated"
    fi
else
    echo ""
    echo "[Step 4/5] Skipping Docker image pull (--skip-docker specified)"
fi

# Step 5: Restart services
if [ "$SKIP_DOCKER" = false ]; then
    echo ""
    echo "[Step 5/5] Restarting services..."
    echo "----------------------------------"
    
    # Restart NSM stack
    if [ -f stacks/nsm/docker-compose.yml ]; then
        echo "Restarting NSM stack..."
        cd stacks/nsm
        $COMPOSE_CMD up -d
        cd "${REPO_ROOT}"
        echo "✓ NSM stack restarted"
    fi
    
    # Restart AI stack
    if [ -f stacks/ai/docker-compose.yml ]; then
        echo "Restarting AI stack..."
        cd stacks/ai
        $COMPOSE_CMD up -d
        cd "${REPO_ROOT}"
        echo "✓ AI stack restarted"
    fi
    
    # Show service status
    echo ""
    echo "Service Status:"
    echo "---------------"
    if [ -f stacks/nsm/docker-compose.yml ]; then
        cd stacks/nsm
        echo "NSM Stack:"
        $COMPOSE_CMD ps
        cd "${REPO_ROOT}"
    fi
    if [ -f stacks/ai/docker-compose.yml ]; then
        cd stacks/ai
        echo ""
        echo "AI Stack:"
        $COMPOSE_CMD ps
        cd "${REPO_ROOT}"
    fi
else
    echo ""
    echo "[Step 5/5] Skipping service restart (--skip-docker specified)"
fi

echo ""
echo "==============================================="
echo "Upgrade Complete!"
echo "==============================================="
echo ""
echo "Next Steps:"
echo "-----------"
echo "1. Check service logs for any errors:"
echo "   cd stacks/nsm && $COMPOSE_CMD logs -f"
echo "   cd stacks/ai && $COMPOSE_CMD logs -f"
echo ""
echo "2. Verify Grafana dashboards are accessible:"
echo "   http://localhost:3000"
echo ""
echo "3. Monitor system health for the next few hours"
echo ""
echo "If issues occur, you can roll back using:"
echo "  git checkout <previous-commit>"
echo "  ./scripts/restore-all.sh <backup-directory>"
echo ""

exit 0

#!/usr/bin/env bash
# Orion Sentinel Upgrade Script
# Safely upgrades the system by backing up, pulling changes, and updating containers

set -euo pipefail

# Determine repo root (script location parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "======================================"
echo "Orion Sentinel - Safe Upgrade"
echo "======================================"
echo ""
echo "Repository Root: ${REPO_ROOT}"
echo ""

# Environment checks
echo "Environment Checks:"
echo "-------------------"

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "✗ git not found"
    exit 1
fi
echo "✓ git installed"

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "✗ docker not found"
    exit 1
fi
echo "✓ docker installed"

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo "✗ docker compose not found"
    exit 1
fi
echo "✓ docker compose installed"

# Check if we're in a git repository
if [ ! -d "${REPO_ROOT}/.git" ]; then
    echo "✗ Not a git repository"
    exit 1
fi
echo "✓ git repository detected"

echo ""

# Show current version
echo "Current State:"
echo "--------------"
CURRENT_COMMIT=$(git -C "${REPO_ROOT}" rev-parse --short HEAD)
CURRENT_BRANCH=$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD)
echo "Branch: ${CURRENT_BRANCH}"
echo "Commit: ${CURRENT_COMMIT}"
git -C "${REPO_ROOT}" --no-pager log -1 --pretty=format:"Date:   %ai%nSubject: %s%n"
echo ""

# Check for uncommitted changes
if [ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]; then
    echo "⚠ Warning: You have uncommitted changes:"
    git -C "${REPO_ROOT}" status --short
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Upgrade cancelled. Please commit or stash your changes."
        exit 0
    fi
fi

echo ""

# Step 1: Create backup
echo "======================================"
echo "Step 1: Creating Backup"
echo "======================================"
echo ""

if [ -x "${SCRIPT_DIR}/backup-all.sh" ]; then
    "${SCRIPT_DIR}/backup-all.sh"
else
    echo "Error: backup-all.sh not found or not executable"
    exit 1
fi

echo ""
read -p "Backup complete. Continue with upgrade? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Upgrade cancelled."
    exit 0
fi

echo ""

# Step 2: Pull latest changes
echo "======================================"
echo "Step 2: Pulling Latest Changes"
echo "======================================"
echo ""

echo "Fetching updates from remote..."
git -C "${REPO_ROOT}" fetch origin

echo ""
echo "Current branch: ${CURRENT_BRANCH}"
REMOTE_COMMIT=$(git -C "${REPO_ROOT}" rev-parse --short origin/${CURRENT_BRANCH} 2>/dev/null || echo "unknown")

if [ "${REMOTE_COMMIT}" = "unknown" ]; then
    echo "⚠ Warning: Cannot determine remote commit. Remote branch may not exist."
    read -p "Continue with 'git pull' anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Upgrade cancelled."
        exit 0
    fi
elif [ "${CURRENT_COMMIT}" = "${REMOTE_COMMIT}" ]; then
    echo "Already up to date! No changes to pull."
    echo ""
else
    echo "Remote commit: ${REMOTE_COMMIT}"
    echo ""
    echo "Changes to be pulled:"
    git -C "${REPO_ROOT}" --no-pager log --oneline ${CURRENT_COMMIT}..origin/${CURRENT_BRANCH} || true
    echo ""
fi

echo "Pulling changes..."
git -C "${REPO_ROOT}" pull origin "${CURRENT_BRANCH}"

echo ""
NEW_COMMIT=$(git -C "${REPO_ROOT}" rev-parse --short HEAD)
echo "Updated to commit: ${NEW_COMMIT}"
echo ""

# Step 3: Update Docker images
echo "======================================"
echo "Step 3: Updating Docker Images"
echo "======================================"
echo ""

# Update NSM stack if it exists
if [ -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" ]; then
    echo "Pulling NSM stack images..."
    docker compose -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" pull || echo "⚠ Warning: Some NSM images could not be pulled"
    echo ""
else
    echo "⊘ NSM stack docker-compose.yml not found"
fi

# Update AI stack if it exists
if [ -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" ]; then
    echo "Pulling AI stack images..."
    docker compose -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" pull || echo "⚠ Warning: Some AI images could not be pulled"
    echo ""
else
    echo "⊘ AI stack docker-compose.yml not found"
fi

# Step 4: Restart services
echo "======================================"
echo "Step 4: Restarting Services"
echo "======================================"
echo ""

# Restart NSM stack
if [ -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" ]; then
    echo "Restarting NSM stack..."
    docker compose -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" up -d
    echo ""
else
    echo "⊘ NSM stack not configured"
fi

# Restart AI stack
if [ -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" ]; then
    echo "Restarting AI stack..."
    docker compose -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" up -d
    echo ""
else
    echo "⊘ AI stack not configured"
fi

# Step 5: Verify services
echo "======================================"
echo "Step 5: Verification"
echo "======================================"
echo ""

echo "Service Status:"
echo "---------------"

if [ -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" ]; then
    echo ""
    echo "NSM Stack:"
    docker compose -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" ps
fi

if [ -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" ]; then
    echo ""
    echo "AI Stack:"
    docker compose -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" ps
fi

echo ""
echo "======================================"
echo "Upgrade Complete!"
echo "======================================"
echo ""
echo "Summary:"
echo "  Previous commit: ${CURRENT_COMMIT}"
echo "  New commit:      ${NEW_COMMIT}"
echo ""
echo "Next steps:"
echo "1. Check service logs for errors:"
echo "   docker compose -f stacks/nsm/docker-compose.yml logs -f"
echo "   docker compose -f stacks/ai/docker-compose.yml logs -f"
echo ""
echo "2. Access Grafana to verify dashboards:"
echo "   http://localhost:3000"
echo ""
echo "3. Test API endpoints:"
echo "   http://localhost:8000/docs"
echo ""
echo "If issues occur, restore from backup:"
echo "   ./scripts/restore-all.sh backups/backup_<timestamp>"
echo ""

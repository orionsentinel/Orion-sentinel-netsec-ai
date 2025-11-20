#!/usr/bin/env bash
#
# upgrade.sh
#
# Safely upgrades Orion Sentinel NSM AI to the latest version
# Performs backup, pulls updates, updates containers, and restarts services
#
# Usage: ./scripts/upgrade.sh
#

set -euo pipefail

# Determine repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==> Orion Sentinel Upgrade"
echo "Repository: ${REPO_ROOT}"
echo ""

# Environment checks
echo "[0/6] Pre-flight checks..."

# Check if we're in a git repository
if ! git -C "${REPO_ROOT}" rev-parse --git-dir > /dev/null 2>&1; then
  echo "Error: Not a git repository"
  exit 1
fi

# Check for uncommitted changes
if [ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]; then
  echo "Warning: You have uncommitted changes in the repository"
  git -C "${REPO_ROOT}" status --short
  echo ""
  echo "Continue anyway? (y/N)"
  read -r response
  if [[ ! "${response}" =~ ^[Yy]$ ]]; then
    echo "Upgrade cancelled. Please commit or stash your changes."
    exit 0
  fi
fi

# Check if docker is available
if ! command -v docker &> /dev/null; then
  echo "Warning: docker command not found"
  echo "Docker operations will be skipped"
  DOCKER_AVAILABLE=false
else
  DOCKER_AVAILABLE=true
fi

echo "   ✓ Pre-flight checks passed"
echo ""

# Backup current state
echo "[1/6] Creating backup..."
if [ -x "${SCRIPT_DIR}/backup-all.sh" ]; then
  "${SCRIPT_DIR}/backup-all.sh"
  echo ""
else
  echo "Error: backup-all.sh not found or not executable"
  exit 1
fi

# Save current commit for reference
CURRENT_COMMIT=$(git -C "${REPO_ROOT}" rev-parse HEAD)
CURRENT_BRANCH=$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD)
echo "Current state: ${CURRENT_BRANCH} @ ${CURRENT_COMMIT:0:8}"
echo ""

# Pull latest changes
echo "[2/6] Pulling latest changes from git..."
cd "${REPO_ROOT}"

# Fetch updates
git fetch origin

# Show what will be updated
UPSTREAM_BRANCH="origin/${CURRENT_BRANCH}"
if git rev-parse --verify "${UPSTREAM_BRANCH}" > /dev/null 2>&1; then
  echo "Changes to be pulled:"
  git log --oneline "${CURRENT_COMMIT}..${UPSTREAM_BRANCH}" | head -10
  echo ""
  
  echo "Pull these changes? (y/N)"
  read -r response
  if [[ ! "${response}" =~ ^[Yy]$ ]]; then
    echo "Upgrade cancelled."
    exit 0
  fi
  
  # Pull changes
  git pull origin "${CURRENT_BRANCH}"
  NEW_COMMIT=$(git rev-parse HEAD)
  echo "   ✓ Updated to ${NEW_COMMIT:0:8}"
else
  echo "Warning: Cannot find upstream branch ${UPSTREAM_BRANCH}"
  echo "Skipping git pull"
fi

echo ""

# Pull latest Docker images
if [ "${DOCKER_AVAILABLE}" = true ]; then
  echo "[3/6] Pulling latest Docker images..."
  
  # NSM stack
  if [ -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" ]; then
    echo "   Pulling NSM stack images..."
    cd "${REPO_ROOT}/stacks/nsm"
    docker compose pull || echo "   ⚠ Failed to pull some NSM images (continuing anyway)"
  fi
  
  # AI stack
  if [ -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" ]; then
    echo "   Pulling AI stack images..."
    cd "${REPO_ROOT}/stacks/ai"
    docker compose pull || echo "   ⚠ Failed to pull some AI images (continuing anyway)"
  fi
  
  echo "   ✓ Docker images updated"
else
  echo "[3/6] Skipping Docker image pull (docker not available)"
fi

echo ""

# Rebuild custom images if needed
if [ "${DOCKER_AVAILABLE}" = true ]; then
  echo "[4/6] Rebuilding custom images..."
  
  # AI stack (has custom Dockerfile)
  if [ -f "${REPO_ROOT}/stacks/ai/Dockerfile" ]; then
    echo "   Rebuilding AI service image..."
    cd "${REPO_ROOT}/stacks/ai"
    docker compose build || echo "   ⚠ Failed to build AI image (continuing anyway)"
  fi
  
  echo "   ✓ Custom images rebuilt"
else
  echo "[4/6] Skipping image rebuild (docker not available)"
fi

echo ""

# Restart services
if [ "${DOCKER_AVAILABLE}" = true ]; then
  echo "[5/6] Restarting services..."
  
  # NSM stack
  if [ -f "${REPO_ROOT}/stacks/nsm/docker-compose.yml" ]; then
    echo "   Restarting NSM stack..."
    cd "${REPO_ROOT}/stacks/nsm"
    docker compose up -d || echo "   ⚠ Failed to start NSM stack"
  fi
  
  # AI stack
  if [ -f "${REPO_ROOT}/stacks/ai/docker-compose.yml" ]; then
    echo "   Restarting AI stack..."
    cd "${REPO_ROOT}/stacks/ai"
    docker compose up -d || echo "   ⚠ Failed to start AI stack"
  fi
  
  echo "   ✓ Services restarted"
else
  echo "[5/6] Skipping service restart (docker not available)"
fi

echo ""

# Verify upgrade
echo "[6/6] Verifying upgrade..."
NEW_COMMIT=$(git -C "${REPO_ROOT}" rev-parse HEAD)
echo "   Previous: ${CURRENT_COMMIT:0:8}"
echo "   Current:  ${NEW_COMMIT:0:8}"

if [ "${DOCKER_AVAILABLE}" = true ]; then
  echo ""
  echo "   Running containers:"
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E "(suricata|loki|grafana|promtail|orion)" || echo "   No Orion containers running"
fi

echo ""
echo "==> Upgrade completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Verify services are running:"
echo "     docker compose ps  (in stacks/nsm/ and stacks/ai/)"
echo "  2. Check logs for errors:"
echo "     docker compose logs -f"
echo "  3. Access Grafana to verify dashboards:"
echo "     http://localhost:3000"
echo "  4. If issues occur, rollback with:"
echo "     git reset --hard ${CURRENT_COMMIT}"
echo "     ./scripts/restore-all.sh backups/backup_<timestamp>"

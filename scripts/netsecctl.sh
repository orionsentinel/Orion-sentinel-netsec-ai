#!/usr/bin/env bash
# Orion Sentinel NetSec Node Control Script
# Manages NSM and AI stacks with SPoG vs standalone modes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NSM_DIR="$PROJECT_ROOT/stacks/nsm"
AI_DIR="$PROJECT_ROOT/stacks/ai"

CMD=${1:-}

show_usage() {
    cat << EOF
Orion Sentinel NetSec Node Control

Usage: $0 {up-spog|up-standalone|down|status|logs}

Commands:
  up-spog        Start in SPoG mode (logs to CoreSrv Loki)
                 Requires LOKI_URL in .env pointing to CoreSrv
  
  up-standalone  Start in standalone/lab mode (local Loki+Grafana)
                 Uses local observability stack for development
  
  down           Stop all services (NSM + AI)
  
  status         Show status of all services
  
  logs           Tail logs from all services

SPoG Mode (Normal Operation):
  - NetSec node = sensor + AI engine
  - All logs/metrics go to CoreSrv Loki
  - Dashboards viewed on CoreSrv Grafana
  - Web UI exposed via CoreSrv Traefik at https://security.local

Standalone Mode (Dev/Lab):
  - NetSec node runs its own Loki + Grafana
  - Useful for development and testing
  - Access Grafana at http://localhost:3000

Examples:
  # Production deployment (SPoG mode)
  $0 up-spog
  
  # Development/testing (standalone mode)
  $0 up-standalone
  
  # Check status
  $0 status
  
  # Stop everything
  $0 down

EOF
}

check_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo "ERROR: .env file not found at $PROJECT_ROOT/.env"
        echo "Copy .env.example to .env and configure LOKI_URL"
        exit 1
    fi
}

up_spog() {
    echo "==> Starting Orion Sentinel in SPoG mode"
    echo "    (NetSec sensor + AI, logs to CoreSrv)"
    echo ""
    
    check_env
    
    # Check LOKI_URL points to CoreSrv
    source "$PROJECT_ROOT/.env"
    # Match http://loki:3100 with or without trailing slash
    if [[ "$LOKI_URL" =~ ^http://loki:3100/?$ ]]; then
        echo "WARNING: LOKI_URL appears to be set to local Loki"
        echo "         For SPoG mode, it should point to CoreSrv (e.g., http://192.168.8.XXX:3100)"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo "Starting NSM stack (Suricata + Promtail)..."
    (cd "$NSM_DIR" && docker compose -f docker-compose.yml up -d)
    
    echo ""
    echo "Starting AI stack..."
    (cd "$AI_DIR" && docker compose up -d)
    
    echo ""
    echo "==> Orion Sentinel started in SPoG mode"
    echo "    View dashboards on CoreSrv Grafana"
    echo "    NetSec UI will be available at https://security.local via CoreSrv Traefik"
}

up_standalone() {
    echo "==> Starting Orion Sentinel in standalone/lab mode"
    echo "    (Local Loki + Grafana for development)"
    echo ""
    
    check_env
    
    echo "Starting NSM stack with local observability..."
    (cd "$NSM_DIR" && docker compose -f docker-compose.yml -f docker-compose.local-observability.yml up -d)
    
    echo ""
    echo "Starting AI stack..."
    (cd "$AI_DIR" && docker compose up -d)
    
    echo ""
    echo "==> Orion Sentinel started in standalone mode"
    echo "    Grafana: http://localhost:3000"
    echo "    NetSec UI: http://localhost:8000"
}

down() {
    echo "==> Stopping Orion Sentinel services"
    
    echo "Stopping AI stack..."
    (cd "$AI_DIR" && docker compose down)
    
    echo ""
    echo "Stopping NSM stack..."
    (cd "$NSM_DIR" && docker compose down)
    
    echo ""
    echo "==> All services stopped"
}

status() {
    echo "==> Orion Sentinel Status"
    echo ""
    echo "NSM Stack:"
    (cd "$NSM_DIR" && docker compose ps)
    
    echo ""
    echo "AI Stack:"
    (cd "$AI_DIR" && docker compose ps)
}

logs_tail() {
    echo "==> Tailing logs (Ctrl+C to exit)"
    echo ""
    
    # Tail logs from both stacks
    docker compose -f "$NSM_DIR/docker-compose.yml" logs -f &
    PID1=$!
    docker compose -f "$AI_DIR/docker-compose.yml" logs -f &
    PID2=$!
    
    # Wait for both
    wait $PID1 $PID2
}

case "$CMD" in
    up-spog)
        up_spog
        ;;
    up-standalone)
        up_standalone
        ;;
    down)
        down
        ;;
    status)
        status
        ;;
    logs)
        logs_tail
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo "ERROR: Unknown command '$CMD'"
        echo ""
        show_usage
        exit 1
        ;;
esac

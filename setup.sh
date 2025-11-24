#!/usr/bin/env bash
# Orion Sentinel NetSec Node - Interactive Setup Script
# Streamlines the installation process with guided configuration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Print colored message
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing_deps=0
    
    # Check Docker
    if command_exists docker; then
        local docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker found: $docker_version"
    else
        print_error "Docker not found. Please install Docker first."
        print_info "Visit: https://docs.docker.com/engine/install/"
        missing_deps=1
    fi
    
    # Check Docker Compose
    if docker compose version >/dev/null 2>&1; then
        local compose_version=$(docker compose version | cut -d' ' -f4)
        print_success "Docker Compose found: $compose_version"
    else
        print_error "Docker Compose not found. Please install Docker Compose."
        print_info "Visit: https://docs.docker.com/compose/install/"
        missing_deps=1
    fi
    
    # Check Git
    if command_exists git; then
        print_success "Git found"
    else
        print_warning "Git not found (optional for development)"
    fi
    
    # Check Python (optional, for development)
    if command_exists python3; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python3 found: $python_version (optional for development)"
    else
        print_warning "Python3 not found (optional, needed only for local development)"
    fi
    
    if [ $missing_deps -eq 1 ]; then
        print_error "Missing required dependencies. Please install them and run setup again."
        exit 1
    fi
    
    print_success "All prerequisites satisfied!"
}

# Select deployment mode
select_mode() {
    print_header "Select Deployment Mode"
    
    echo "Orion Sentinel NetSec supports two deployment modes:"
    echo ""
    echo "  1) SPoG Mode (Production - Recommended)"
    echo "     - NetSec node acts as a sensor reporting to CoreSrv"
    echo "     - All logs/metrics sent to centralized CoreSrv Loki"
    echo "     - Dashboards viewed on CoreSrv Grafana"
    echo "     - Requires CoreSrv with Loki running"
    echo ""
    echo "  2) Standalone Mode (Development/Lab)"
    echo "     - NetSec node runs with local Loki + Grafana"
    echo "     - All observability stays local"
    echo "     - Useful for development, testing, or offline operation"
    echo ""
    
    while true; do
        read -p "Select mode (1 for SPoG, 2 for Standalone): " mode_choice
        case $mode_choice in
            1)
                DEPLOY_MODE="spog"
                print_success "Selected: SPoG Mode"
                break
                ;;
            2)
                DEPLOY_MODE="standalone"
                print_success "Selected: Standalone Mode"
                break
                ;;
            *)
                print_error "Invalid choice. Please enter 1 or 2."
                ;;
        esac
    done
}

# Configure environment
configure_environment() {
    print_header "Environment Configuration"
    
    if [ -f .env ]; then
        print_warning ".env file already exists"
        read -p "Overwrite existing .env file? (y/N): " overwrite
        if [[ ! $overwrite =~ ^[Yy]$ ]]; then
            print_info "Keeping existing .env file"
            return
        fi
    fi
    
    # Copy example
    cp .env.example .env
    print_success "Created .env file from .env.example"
    
    # Configure based on mode
    if [ "$DEPLOY_MODE" = "spog" ]; then
        configure_spog_mode
    else
        configure_standalone_mode
    fi
    
    # Common configuration
    configure_common_settings
}

# Configure SPoG mode settings
configure_spog_mode() {
    print_info "Configuring SPoG mode settings..."
    
    echo ""
    echo "SPoG mode requires CoreSrv with Loki running on your network."
    read -p "Enter CoreSrv Loki URL (e.g., http://192.168.8.50:3100): " loki_url
    
    if [ -z "$loki_url" ]; then
        print_warning "No URL provided, using default: http://192.168.8.50:3100"
        loki_url="http://192.168.8.50:3100"
    fi
    
    # Update .env file
    sed -i "s|LOKI_URL=.*|LOKI_URL=$loki_url|g" .env
    sed -i "s|LOCAL_OBSERVABILITY=.*|LOCAL_OBSERVABILITY=false|g" .env
    
    print_success "Configured for SPoG mode with Loki at: $loki_url"
}

# Configure standalone mode settings
configure_standalone_mode() {
    print_info "Configuring Standalone mode settings..."
    
    # Update .env file
    sed -i "s|LOKI_URL=.*|LOKI_URL=http://loki:3100|g" .env
    sed -i "s|LOCAL_OBSERVABILITY=.*|LOCAL_OBSERVABILITY=true|g" .env
    
    print_success "Configured for Standalone mode with local Loki"
}

# Configure common settings
configure_common_settings() {
    echo ""
    print_info "Configuring common settings..."
    
    # Network interface
    echo ""
    echo "Available network interfaces:"
    ip link show | grep -E '^[0-9]+:' | awk '{print "  - " $2}' | sed 's/:$//'
    echo ""
    read -p "Enter network interface for Suricata (e.g., eth0, default: eth0): " nsm_iface
    nsm_iface=${nsm_iface:-eth0}
    
    # Add NSM_IFACE to .env if not present
    if grep -q "^NSM_IFACE=" .env; then
        sed -i "s|NSM_IFACE=.*|NSM_IFACE=$nsm_iface|g" .env
    else
        echo "" >> .env
        echo "# Network Interface for Suricata" >> .env
        echo "NSM_IFACE=$nsm_iface" >> .env
    fi
    
    print_success "Network interface set to: $nsm_iface"
    
    # SOAR dry run mode
    echo ""
    read -p "Enable SOAR dry-run mode? (recommended for first installation) (Y/n): " soar_dry_run
    if [[ ! $soar_dry_run =~ ^[Nn]$ ]]; then
        sed -i "s|SOAR_DRY_RUN=.*|SOAR_DRY_RUN=1|g" .env
        print_success "SOAR dry-run mode enabled (safe mode)"
    else
        sed -i "s|SOAR_DRY_RUN=.*|SOAR_DRY_RUN=0|g" .env
        print_warning "SOAR dry-run mode disabled (actions will be executed)"
    fi
    
    echo ""
    print_success "Environment configuration complete!"
    print_info "You can further customize settings by editing .env file"
}

# Setup Python development environment
setup_python_dev() {
    print_header "Python Development Environment Setup"
    
    if ! command_exists python3; then
        print_warning "Python3 not found. Skipping Python development setup."
        return
    fi
    
    read -p "Set up Python development environment? (y/N): " setup_dev
    if [[ ! $setup_dev =~ ^[Yy]$ ]]; then
        print_info "Skipping Python development environment setup"
        return
    fi
    
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    
    print_info "Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    pip install -r requirements-dev.txt
    
    print_success "Python development environment created!"
    print_info "Activate with: source venv/bin/activate"
}

# Display next steps
show_next_steps() {
    print_header "Installation Complete!"
    
    echo "✅ Environment configured"
    echo "✅ Ready to start services"
    echo ""
    
    if [ "$DEPLOY_MODE" = "spog" ]; then
        echo "Next steps for SPoG mode:"
        echo ""
        echo "  1. Verify CoreSrv Loki is accessible:"
        echo "     curl \$(grep LOKI_URL .env | cut -d= -f2)/ready"
        echo ""
        echo "  2. Start services:"
        echo "     ./scripts/netsecctl.sh up-spog"
        echo ""
        echo "  3. Verify log shipping:"
        echo "     docker logs orion-promtail | grep POST"
        echo ""
        echo "  4. Access via CoreSrv:"
        echo "     - Dashboards: https://grafana.local (on CoreSrv)"
        echo "     - NetSec Web UI: https://security.local (via CoreSrv Traefik)"
        echo ""
        echo "  5. Configure Traefik on CoreSrv (if not already done):"
        echo "     See: docs/CORESRV-INTEGRATION.md"
        echo ""
    else
        echo "Next steps for Standalone mode:"
        echo ""
        echo "  1. Start services:"
        echo "     ./scripts/netsecctl.sh up-standalone"
        echo ""
        echo "  2. Access services:"
        echo "     - Grafana: http://localhost:3000 (admin/admin)"
        echo "     - NetSec Web UI: http://localhost:8000"
        echo "     - Loki API: http://localhost:3100"
        echo ""
        echo "  3. Verify services:"
        echo "     ./scripts/netsecctl.sh status"
        echo ""
    fi
    
    echo "Common operations:"
    echo "  - View logs: ./scripts/netsecctl.sh logs"
    echo "  - Check status: ./scripts/netsecctl.sh status"
    echo "  - Stop services: ./scripts/netsecctl.sh down"
    echo "  - Get help: ./scripts/netsecctl.sh help"
    echo ""
    echo "Documentation:"
    echo "  - Quick Start: QUICKSTART.md"
    echo "  - Full README: README.md"
    echo "  - Architecture: docs/architecture.md"
    echo ""
    
    print_success "Setup complete! Ready to deploy Orion Sentinel NetSec."
}

# Main installation flow
main() {
    clear
    print_header "🛡️  Orion Sentinel NetSec Node - Interactive Setup"
    
    echo "This script will guide you through setting up Orion Sentinel NetSec."
    echo "It will:"
    echo "  - Check prerequisites (Docker, Docker Compose)"
    echo "  - Help you choose deployment mode (SPoG vs Standalone)"
    echo "  - Configure environment variables"
    echo "  - Optionally set up Python development environment"
    echo ""
    
    read -p "Continue with setup? (Y/n): " continue_setup
    if [[ $continue_setup =~ ^[Nn]$ ]]; then
        print_info "Setup cancelled"
        exit 0
    fi
    
    # Run setup steps
    check_prerequisites
    select_mode
    configure_environment
    setup_python_dev
    show_next_steps
}

# Run main
main

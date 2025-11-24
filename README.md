# Orion Sentinel - NetSec Node

**AI-Powered Network Security Monitoring & Threat Detection for Home Labs**

Orion Sentinel NetSec is a network security sensor and AI-powered threat detection engine designed for home labs and small networks. This repository contains the **NetSec node** component that runs on a Raspberry Pi 5 or mini-PC.

## 🏗️ Architecture: Single Pane of Glass (SPoG)

The Orion Sentinel platform consists of two main components:

```
┌─────────────────────────────────────────────────────────────────┐
│                   CoreSrv (Dell) - SPoG                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Single Pane of Glass - All Observability & Dashboards    │ │
│  │  • Traefik + Authelia (SSO & reverse proxy)               │ │
│  │  • Loki (central log aggregation)                          │ │
│  │  • Prometheus (metrics collection)                         │ │
│  │  • Grafana (all dashboards)                                │ │
│  │  • Uptime-Kuma (service monitoring)                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────▲──────────────────────────────────────┘
                           │
                           │ Logs & Metrics
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│            NetSec Node (Pi 5) - This Repository                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Sensor + AI Engine (No Dashboards in Production)         │ │
│  │  • Suricata IDS (passive monitoring)                       │ │
│  │  • AI threat detection & correlation                       │ │
│  │  • SOAR automation                                         │ │
│  │  • Promtail (ships logs to CoreSrv)                        │ │
│  │  • Web UI (exposed via CoreSrv Traefik)                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Modes

Orion Sentinel NetSec supports two explicit deployment modes:

### 🎯 SPoG Mode (Integrated with CoreSrv)

**Purpose**: NetSec node acts as a sensor feeding into a centralized CoreSrv for observability.

**Configuration**:
- `.env` settings:
  - `LOCAL_OBSERVABILITY=false`
  - `LOKI_URL=http://<CoreSrv-IP>:3100` (e.g., `http://192.168.8.50:3100`)
- Docker Compose files: Use only `stacks/nsm/docker-compose.yml`
- Startup command: `./scripts/netsecctl.sh up-spog`

**What runs**:
- NetSec = sensor + AI engine only
- All logs shipped to CoreSrv Loki
- All dashboards on CoreSrv Grafana
- Web UI accessed via CoreSrv Traefik at `https://security.local`
- No local Loki/Grafana on NetSec node

### 🧪 Standalone Mode (Local Observability)

**Purpose**: NetSec node runs completely on its own with local Loki and Grafana for development, testing, or offline operation.

**Configuration**:
- `.env` settings:
  - `LOCAL_OBSERVABILITY=true`
  - `LOKI_URL=http://loki:3100`
- Docker Compose files: Use `stacks/nsm/docker-compose.yml` + `stacks/nsm/docker-compose.local-observability.yml`
- Startup command: `./scripts/netsecctl.sh up-standalone`

**What runs**:
- NetSec runs its own Loki + Grafana stack
- All observability stays local on the NetSec node
- Access Grafana at `http://localhost:3000`
- Access Web UI at `http://localhost:8000`
- Useful for development, testing, and offline operation

---

See [CoreSrv Integration Guide](docs/CORESRV-INTEGRATION.md) for setup details.

## What Makes Orion Sentinel Different?

Orion Sentinel occupies a unique space in the home/small-office security landscape:

**vs. Firewalla / UniFi Threat Management:**
- ✅ **Open & hackable**: All components visible and configurable—no black boxes
- ✅ **Runs on your hardware**: Pi 4/5 or any mini-PC you already own
- ✅ **Full observability**: Loki + Grafana give you complete visibility into what's happening
- ❌ Not as polished or plug-and-play (by design—you're in control)

**vs. Security Onion / Wazuh / SELKS:**
- ✅ **Home/SOHO scale**: Designed for single Pi or mini-PC, not multi-node clusters
- ✅ **Lower complexity**: Docker Compose deployment, not Kubernetes or complex installers
- ✅ **Pi-friendly**: Optimized for ARM and constrained resources
- ❌ Not enterprise-grade (not intended for 1000+ endpoints or 24/7 SOC teams)

**The Orion Sentinel Niche:**
- One network (home/lab/small office), not a corporate SOC
- Transparent architecture you can understand and modify
- AI that explains its reasoning, not just scores
- SOAR that can act on your network (Pi-hole, router, notifications)
- Learning-friendly: See how modern security stacks work in practice

## Key Features

### 🔍 Network Security Monitoring (NSM)
- **Suricata IDS/IPS**: Passive traffic monitoring with signature-based detection
- **Loki log aggregation**: Centralized storage for all security, DNS, and system logs
- **Promtail log shipping**: Unified log collection from all sources
- Real-time network traffic analysis via mirrored/SPAN port

### 🤖 AI-Assisted Detection
- **AI correlation engine**: Analyzes Suricata alerts, DNS queries, device inventory, and threat intel
- **Risk scoring with context**: Each event gets a score + human-readable explanation
- **Device anomaly detection**: Behavioral analysis per device
- **Domain risk scoring**: DGA detection, phishing identification, C2 domain spotting
- **Threat intelligence integration**:
  - AlienVault OTX (community threat exchange)
  - abuse.ch URLhaus (malicious URLs)
  - abuse.ch Feodo Tracker (botnet C2s)
  - PhishTank (verified phishing sites)
  - Automatic IOC enrichment and risk boosting

### ⚡ SOAR & Automated Response
- **Playbook-based automation**: Event-driven actions with YAML configuration
- **Built-in actions**:
  - Block domains via Pi-hole DNS
  - Send notifications (Email, Signal, Telegram, Webhook)
  - Tag devices or change profiles
  - Custom scripts/webhooks
- **Safety controls**:
  - Dry-run mode (test before enforce)
  - Priority-based execution
  - Lab mode (device-based policy segregation)
  - Full audit logging
- **Web UI for playbook management**: Enable/disable, test, and monitor playbooks

### 📊 Observability & Dashboards
- **Grafana integration**: Real-time dashboards with 30s refresh
  - SOC Management: Health score, key metrics, recent events
  - DNS & Pi-hole: Query analysis, block rates, top domains
  - Custom dashboards: Build your own views
- **Web dashboard** (port 8080):
  - Health score and security overview
  - Searchable event log with filters
  - Complete device inventory
  - Playbook management interface
- **JSON REST APIs**: All pages available as JSON for automation

### 🏠 Home/SOHO & Lab-Friendly
- **Docker Compose deployment**: Simple stack management, no Kubernetes required
- **Designed for constrained hardware**:
  - Raspberry Pi 4/5 (4-8GB RAM)
  - Intel N100 or similar mini-PC
  - Single-box deployment
- **Lab mode**: Safe testing with device-based segregation
- **Low maintenance**: Auto-provisioned dashboards, configurable retention, minimal tuning

### 🔧 Additional Features
- **📢 Multi-channel notifications**: Email (SMTP), Signal, Telegram, webhooks with rich alert formatting
- **📊 Device inventory & fingerprinting**: Automatic discovery, type classification (IoT, TV, NAS), tagging, risk scoring
- **📈 Security health score**: Single 0-100 metric with weighted components and actionable recommendations
- **🖥️ EDR-lite**: Host log integration (Wazuh, osquery, syslog) with normalized event model
- **🍯 Honeypot integration**: External honeypot container support for high-confidence threat detection
- **🔍 Change detection**: Baseline snapshots, behavioral change alerts, "what changed?" analysis

## Architecture

Orion Sentinel runs as two Docker Compose stacks on a single device (Raspberry Pi or mini-PC):

```
┌─────────────────────────────────────────────────────────────────┐
│                     Pi/Mini-PC (Docker Host)                    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐│
│  │              Stack: NSM (Network Monitoring)               ││
│  │  ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐   ││
│  │  │ Suricata │─▶│Promtail │─▶│  Loki   │◀─│ Grafana  │   ││
│  │  │   IDS    │  │         │  │  Logs   │  │Dashboard │   ││
│  │  └────▲─────┘  └─────────┘  └────▲────┘  └──────────┘   ││
│  │       │                           │                       ││
│  └───────┼───────────────────────────┼───────────────────────┘│
│          │ Mirrored                  │                        │
│          │ Traffic                   │                        │
│  ┌───────┴───────────────────────────┼───────────────────────┐│
│  │              Stack: AI (Detection & Response)             ││
│  │  ┌──────────────────────────────┐ │                       ││
│  │  │      AI Engine & SOAR        │ │                       ││
│  │  │  ┌────────────────────────┐  │ │                       ││
│  │  │  │ Inventory Service      │──┼─┘  Read/Write Events   ││
│  │  │  │ SOAR Service           │  │                         ││
│  │  │  │ Health Score Service   │  │                         ││
│  │  │  │ Threat Intel Sync      │  │                         ││
│  │  │  │ Change Monitor         │  │                         ││
│  │  │  └────────────────────────┘  │                         ││
│  │  │  ┌────────────────────────┐  │                         ││
│  │  │  │ Web UI (Port 8080)     │  │                         ││
│  │  │  │ - Dashboard            │  │                         ││
│  │  │  │ - Events               │  │                         ││
│  │  │  │ - Devices              │  │                         ││
│  │  │  │ - Playbooks            │  │                         ││
│  │  │  └────────────────────────┘  │                         ││
│  │  └──────────┬───────────────────┘                         ││
│  │             │ Actions                                     ││
│  │             ▼                                              ││
│  │  ┌────────────────────────┐                               ││
│  │  │  Pi-hole / Router APIs │  (Optional)                   ││
│  │  │  Notification Services │                               ││
│  │  └────────────────────────┘                               ││
│  └───────────────────────────────────────────────────────────┘│
│         ▲                                                      │
│         │ Port Mirror / SPAN                                  │
└─────────┼──────────────────────────────────────────────────────┘
          │
    ┌─────┴──────┐
    │   Router   │
    │  / Switch  │
    └────────────┘
```

### Data Flow (in 5 steps)

1. **Network traffic capture**: Router/switch mirrors LAN traffic → Suricata IDS captures and analyzes
2. **Log centralization**: Suricata alerts, flows, DNS → Promtail → Loki (also receives logs from Pi-hole, host agents)
3. **AI analysis**: AI services read logs from Loki → correlate events, score risks, enrich with threat intel
4. **Event generation**: AI produces SecurityEvents with scores + explanations → written back to Loki
5. **Automated response**: SOAR reads high-risk events → executes playbooks (block domains, notify, tag devices)

Everything flows through Loki and is visible in both Grafana (analytics) and the Web UI (operational view).

## Quick Start

### Prerequisites

- Raspberry Pi 5 (8GB) or mini-PC with Docker
- Docker & Docker Compose installed
- Network switch/router with port mirroring (SPAN) configured
- CoreSrv running (for SPoG mode) OR standalone lab setup

### 🚀 Streamlined Installation (Recommended)

The easiest way to get started:

```bash
# 1. Clone repository
git clone https://github.com/yorgosroussakis/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai

# 2. Run interactive setup
./setup.sh
# OR using Make
make setup

# 3. Start services (based on mode you selected)
make start-spog        # For SPoG mode
# OR
make start-standalone  # For Standalone mode
```

The interactive setup script will:
- ✅ Check all prerequisites (Docker, Docker Compose)
- ✅ Guide you through mode selection (SPoG vs Standalone)
- ✅ Configure environment variables with prompts
- ✅ Set network interface for Suricata
- ✅ Optionally set up Python development environment
- ✅ Display clear next steps

### Manual Installation (Alternative)

If you prefer manual configuration:

#### SPoG Mode (Production - Recommended)

Deploy NetSec as a sensor that reports to CoreSrv:

1. **Clone repository**:
   ```bash
   git clone https://github.com/yorgosroussakis/Orion-sentinel-netsec-ai.git
   cd Orion-sentinel-netsec-ai
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Set the following:
   ```bash
   # Point to your CoreSrv Loki instance
   LOKI_URL=http://192.168.8.XXX:3100  # Replace XXX with CoreSrv IP
   LOCAL_OBSERVABILITY=false
   
   # Set network interface for Suricata (your mirrored port)
   NSM_IFACE=eth0
   
   # Configure Pi-hole, notifications, etc. as needed
   ```

3. **Start services**:
   ```bash
   ./scripts/netsecctl.sh up-spog
   # OR
   make start-spog
   ```

4. **Verify log shipping**:
   ```bash
   docker logs orion-promtail | grep "POST"
   # Should see: POST /loki/api/v1/push (200 OK)
   ```

5. **Access via CoreSrv**:
   - **Dashboards**: https://grafana.local (on CoreSrv)
   - **NetSec Web UI**: https://security.local (via CoreSrv Traefik)
   - **Logs**: Grafana Explore → `{host="pi-netsec"}`

See [CoreSrv Integration Guide](docs/CORESRV-INTEGRATION.md) for detailed setup.

#### Standalone Mode (Development/Lab)

Run NetSec with local observability for development:

1. **Clone and configure** (as above)

2. **Set environment for standalone**:
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Set:
   ```bash
   LOKI_URL=http://loki:3100
   LOCAL_OBSERVABILITY=true
   ```

3. **Start with local observability**:
   ```bash
   ./scripts/netsecctl.sh up-standalone
   ```

4. **Access local services**:
   - **Grafana**: http://localhost:3000 (admin/admin)
   - **NetSec Web UI**: http://localhost:8000
   - **Loki API**: http://localhost:3100

### Common Commands

#### Using Make (Recommended)

```bash
# Get help with all available commands
make help

# Service management
make start-spog          # Start in SPoG mode
make start-standalone    # Start in Standalone mode
make stop               # Stop all services
make status             # Check service status
make logs              # View logs

# Development
make dev-install       # Set up Python development environment
make test             # Run tests
make lint             # Run linters
```

#### Using netsecctl.sh Script

```bash
# Check service status
./scripts/netsecctl.sh status

# View logs
./scripts/netsecctl.sh logs

# Stop all services
./scripts/netsecctl.sh down

# Get help
./scripts/netsecctl.sh help
```

### Development Setup

For Python development:

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .

# Run individual services locally
python -m orion_ai.soar.service
python -m orion_ai.inventory.service
python -m orion_ai.health_score.service
```

## Configuration

All configuration is via environment variables in `.env` file. See [.env.example](.env.example) for all options.

### Key Settings

**Loki Connection** (SPoG Integration):
- `LOKI_URL` - CoreSrv Loki URL (e.g., `http://192.168.8.XXX:3100`)
- `LOCAL_OBSERVABILITY` - Enable local Loki+Grafana (`true`/`false`)

**SOAR Automation:**
- `SOAR_DRY_RUN=1` - Enable dry run mode (recommended initially)
- `SOAR_POLL_INTERVAL=60` - Event polling interval in seconds

**Notifications** ([Setup Guide](docs/notifications.md)):
- `NOTIFY_SMTP_HOST` / `NOTIFY_SMTP_USER` / `NOTIFY_SMTP_PASS` - Email via SMTP
- `NOTIFY_SIGNAL_ENABLED` / `NOTIFY_SIGNAL_API_URL` - Signal messenger
- `NOTIFY_TELEGRAM_ENABLED` / `NOTIFY_TELEGRAM_BOT_TOKEN` - Telegram bot

**Threat Intelligence** ([Integration Guide](docs/threat-intel.md)):
- `TI_ENABLE_OTX=true` / `TI_OTX_API_KEY` - AlienVault OTX
- `TI_ENABLE_URLHAUS=true` - abuse.ch URLhaus
- `TI_ENABLE_FEODO=true` - abuse.ch Feodo Tracker
- `TI_ENABLE_PHISHTANK=true` - PhishTank

**Pi-hole Integration:**
- `PIHOLE_URL=http://192.168.1.2` - Pi-hole instance URL
- `PIHOLE_API_KEY=xxx` - Pi-hole API key for blocking

**Web UI:**
- `API_HOST=0.0.0.0` / `API_PORT=8080` - Web interface binding

See [.env.example](.env.example) for complete configuration options.

## Documentation

### SPoG Integration
- [CoreSrv Integration](docs/CORESRV-INTEGRATION.md) 🎯 **Integration Guide**
- [CoreSrv Dashboards](docs/CORESRV-DASHBOARDS.md) 📊 **Dashboard Export**

### Core Features
- [SOAR Playbooks](docs/soar.md)
- [Notifications & Alerts](docs/notifications.md) 📢
- [Threat Intelligence](docs/threat-intel.md) 🛡️
- [Web Dashboard](docs/web-ui.md) 🌐
- [Device Inventory](docs/inventory.md)
- [Change Monitor](docs/change-monitor.md)
- [Health Score](docs/health-score.md)

### Stacks & Setup
- [NSM Stack](stacks/nsm/README.md) - Suricata + Promtail
- [AI Stack](stacks/ai/README.md) - AI services
- [Architecture](docs/architecture.md) - System design

### Additional
- [Lab Mode](docs/lab-mode.md)
- [Host Logs (EDR-lite)](docs/host-logs.md)
- [Honeypot Integration](src/orion_ai/honeypot/design.md)

## Module Structure

```
src/orion_ai/
├── soar/                  # SOAR automation
│   ├── models.py          # Data models
│   ├── engine.py          # Playbook engine
│   ├── actions.py         # Action executors
│   └── service.py         # SOAR service
├── notifications/         # 📢 Multi-channel alerts
│   ├── models.py          # Notification data models
│   ├── providers.py       # Email, Signal, Telegram, Webhook
│   ├── dispatcher.py      # Notification routing
│   └── formatters.py      # Event to notification conversion
├── threat_intel/          # 🛡️ Threat intelligence
│   ├── ioc_models.py      # IOC data models
│   ├── ioc_fetchers.py    # OTX, URLhaus, Feodo, PhishTank
│   ├── store.py           # SQLite IOC storage
│   ├── lookup.py          # Fast IOC lookups
│   └── sync.py            # Feed synchronization CLI
├── inventory/             # Device inventory
│   ├── models.py
│   ├── collector.py       # Log collection
│   ├── fingerprinting.py
│   ├── store.py           # SQLite storage
│   └── service.py
├── ui/                    # 🌐 Web dashboard
│   ├── api.py             # FastAPI routes
│   ├── views.py           # View logic
│   └── templates/         # HTML templates
│       ├── dashboard.html
│       ├── events.html
│       ├── devices.html
│       └── playbooks.html # Playbook management
├── host_logs/             # EDR-lite
│   ├── models.py
│   └── normalizer.py      # Log normalization
├── honeypot/              # Honeypot integration
│   └── design.md
├── change_monitor/        # Change detection
│   ├── models.py
│   ├── baseline.py
│   ├── analyzer.py
│   └── service.py
└── health_score/          # Security health score
    ├── models.py
    ├── calculator.py
    └── service.py
```

## API Examples

### Web UI Pages

```bash
# Dashboard with health score and recent events
http://localhost:8080/

# Security events log (searchable, filterable)
http://localhost:8080/events

# Device inventory
http://localhost:8080/devices

# SOAR playbook management
http://localhost:8080/playbooks
```

### JSON API Endpoints

```bash
# Get recent events
curl http://localhost:8080/api/events?limit=50&hours=24

# Get device list
curl http://localhost:8080/api/devices

# Get device profile
curl http://localhost:8080/api/device/192.168.1.50

# List playbooks
curl http://localhost:8080/api/playbooks

# Toggle playbook
curl -X POST http://localhost:8080/api/playbooks/alert-high-risk-domain/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Get health score
curl http://localhost:8080/api/health
```

### Threat Intelligence CLI

```bash
# Sync threat intel feeds
docker-compose exec ai-service python -m orion_ai.threat_intel.sync --hours 24

# View IOC statistics
docker-compose exec ai-service python -m orion_ai.threat_intel.sync --stats
```

## Safety & Testing

### Initial Deployment

1. **Start in dry run mode**: `SOAR_DRY_RUN=1`
2. **Review logs**: Check what actions would be taken
3. **Test on lab devices**: Tag devices with `lab` tag
4. **Gradually enable**: One playbook at a time
5. **Monitor closely**: Watch for false positives

### Production Checklist

- [ ] All playbooks tested in dry run
- [ ] Lab devices tagged and tested
- [ ] High confidence thresholds set (≥0.9)
- [ ] Rollback plan documented
- [ ] Monitoring dashboards configured
- [ ] Team trained on SOAR interface

## Contributing

This is a personal home/lab project, but suggestions and feedback are welcome via issues.

## License

MIT License - See LICENSE file

## Related Projects

- [orion-sentinel-dns-ha](https://github.com/yorgosroussakis/orion-sentinel-dns-ha): DNS & HA component (Pi-hole + Unbound + Keepalived)

## Roadmap

### ✅ v0.2 - SOC-in-a-Box (Current)
- [x] Multi-channel notifications (Email, Signal, Telegram, Webhook)
- [x] Threat intelligence integration (OTX, URLhaus, Feodo, PhishTank)
- [x] Web UI for playbook management
- [x] Event enrichment with TI context
- [x] Comprehensive documentation

### 🚧 v0.3 - AI & Detection (In Progress)
- [ ] AI model integration (ONNX/TFLite on Pi AI Hat)
- [ ] Domain risk scoring with ML
- [ ] Device anomaly detection
- [ ] Template variable resolution in playbooks
- [ ] MITRE ATT&CK mapping

### 📋 v0.4 - Advanced Features (Planned)
- [ ] Pi-hole blocking automation (production-ready)
- [ ] Advanced Grafana dashboards
- [ ] Scheduled playbook execution
- [ ] Incident management workflow
- [ ] Custom threat intel feeds
- [ ] API authentication

## Acknowledgments

Built for learning and home lab security. Inspired by enterprise SOC platforms adapted for Raspberry Pi constraints.
# Orion Sentinel NSM + AI

**Network Security Monitoring & AI-Powered Threat Detection for Home/Lab Networks**

This repository is the **Security & Monitoring (NSM + AI)** component of the Orion Sentinel home/lab security project. It runs on a Raspberry Pi 5 (8 GB) with an AI Hat to provide passive network monitoring, anomaly detection, and automated threat response.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Home/Lab Network                            │
│                                                                     │
│  ┌──────────────┐         ┌─────────────┐        ┌──────────────┐ │
│  │   Router     │         │   Pi #1     │        │   Pi #2      │ │
│  │  (GL.iNet)   │────────▶│  DNS + HA   │───────▶│ NSM + AI     │ │
│  │              │         │             │        │ (This Repo)  │ │
│  │ - NAT        │         │ - Pi-hole   │        │              │ │
│  │ - Firewall   │         │ - Unbound   │        │ - Suricata   │ │
│  │ - DHCP       │         │ - Keepalived│        │ - Loki       │ │
│  │ - VPN        │         │             │        │ - Grafana    │ │
│  │              │         │ Exposes:    │        │ - AI Service │ │
│  └──────┬───────┘         │ - DNS Logs  │        │              │ │
│         │                 │ - API       │        │ Role:        │ │
│         │                 └─────────────┘        │ - Passive    │ │
│         │ Port                                   │   Sensor     │ │
│         │ Mirror                                 │ - AI Detect  │ │
│         └────────────────────────────────────────▶│ - Dashboards│ │
│                                                   └──────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

Data Flows:
  1. Router mirrors ALL LAN traffic → Pi #2 (Suricata)
  2. Pi #1 ships DNS logs (Pi-hole + Unbound) → Pi #2 (Loki)
  3. Pi #2 AI analyzes NSM + DNS logs → detects anomalies
  4. Pi #2 optionally calls Pi-hole API → blocks high-risk domains
```

## 🎯 What This Repo Does

**Pi #2 (Security Pi)** acts as a **passive network security sensor** with AI-powered threat detection:

### Network Security Monitoring (NSM)
- **Suricata** IDS in passive mode on mirrored traffic interface
- **Loki** for centralized log storage (NSM + DNS + AI events)
- **Promtail** to ship logs from Suricata and AI service to Loki
- **Grafana** for visualization and dashboards

### AI-Powered Detection
- Python service using the Raspberry Pi AI Hat (~13 TOPS)
- Two main detection pipelines:
  1. **Device Anomaly Detection**: Analyzes per-device behavior (connections, bytes, DNS patterns)
  2. **Domain Risk Scoring**: Identifies suspicious domains (DGA, phishing, C2)
- Uses pre-trained ONNX/TFLite models for inference
- **Threat Intelligence Integration**: Cross-references domains/IPs against known IOCs from:
  - AlienVault OTX (Open Threat Exchange)
  - abuse.ch URLhaus (malicious URLs)
  - abuse.ch Feodo Tracker (botnet C2 servers)
  - PhishTank (verified phishing sites)
- Automatic risk score boosting on threat intel matches
- Writes anomaly events as structured logs to Loki

### Automated Response
- Pi-hole API integration for automated domain blocking
- Policy-based enforcement: high-risk domains → blocklist
- All actions logged for audit and transparency

## 📁 Repository Structure

```
orion-sentinel-nsm-ai/
├── README.md                           # This file
├── docs/                               # Documentation
│   ├── architecture.md                 # Detailed architecture & data flows
│   ├── pi2-setup.md                    # Raspberry Pi 5 setup guide
│   ├── logging-and-dashboards.md       # Loki & Grafana setup
│   ├── ai-stack.md                     # AI service design & models
│   └── integration-orion-dns-ha.md     # DNS integration with Pi #1
├── stacks/
│   ├── nsm/                            # Network Security Monitoring stack
│   │   ├── docker-compose.yml          # Suricata, Loki, Promtail, Grafana
│   │   ├── suricata/
│   │   │   └── suricata.yaml           # Suricata IDS configuration
│   │   ├── promtail/
│   │   │   └── promtail-config.yml     # Log shipping configuration
│   │   ├── loki/
│   │   │   └── loki-config.yaml        # Loki storage configuration
│   │   └── grafana/
│   │       └── datasources.yml         # Grafana datasource config
│   └── ai/                             # AI detection service
│       ├── docker-compose.yml          # AI service container
│       ├── Dockerfile                  # Python AI service image
│       ├── requirements.txt            # Python dependencies
│       ├── models/                     # ONNX/TFLite model directory
│       ├── src/
│       │   └── orion_ai/               # Python package
│       │       ├── __init__.py
│       │       ├── config.py           # Configuration management
│       │       ├── log_reader.py       # Read logs from Loki
│       │       ├── feature_extractor.py# Build feature vectors
│       │       ├── model_runner.py     # ML model inference
│       │       ├── pipelines.py        # Detection pipelines
│       │       ├── output_writer.py    # Write results to Loki
│       │       ├── http_server.py      # Optional API server
│       │       └── pihole_client.py    # Pi-hole API client
│       └── main.py                     # Entry point
└── .gitignore
```

## 🚀 Quick Start

### Prerequisites
- Raspberry Pi 5 (8 GB RAM recommended)
- Raspberry Pi AI Hat installed
- Raspberry Pi OS 64-bit (Debian Bookworm or later)
- Docker & Docker Compose installed
- Network switch/router configured to mirror LAN traffic to Pi #2's interface
- Access to Pi #1's Pi-hole API (from `orion-sentinel-dns-ha` repo)

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/orion-sentinel-nsm-ai.git
cd orion-sentinel-nsm-ai

# Copy and edit environment files
cp stacks/nsm/.env.example stacks/nsm/.env
cp stacks/ai/.env.example stacks/ai/.env
```

### 2. Configure Network Interface

Edit `stacks/nsm/.env` and set your mirrored traffic interface:
```bash
NSM_IFACE=eth0  # Replace with your actual interface (e.g., eth1, wlan0)
```

### 3. Start NSM Stack

```bash
cd stacks/nsm
docker compose up -d
```

Verify services:
- Grafana: http://pi2-ip:3000 (default: admin/admin)
- Loki API: http://pi2-ip:3100

### 4. Start AI Service

```bash
cd stacks/ai
# Place your models in ./models/ directory
docker compose up -d
```

### 5. Configure DNS Log Shipping (on Pi #1)

See `docs/integration-orion-dns-ha.md` for detailed instructions on configuring Pi #1 to ship DNS logs to this Pi's Loki instance.

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [architecture.md](docs/architecture.md) | Detailed system architecture, components, and data flows |
| [pi2-setup.md](docs/pi2-setup.md) | Step-by-step Raspberry Pi 5 setup and prerequisites |
| [logging-and-dashboards.md](docs/logging-and-dashboards.md) | Loki configuration, log querying, and Grafana dashboards |
| [ai-stack.md](docs/ai-stack.md) | AI service design, model formats, and inference details |
| [integration-orion-dns-ha.md](docs/integration-orion-dns-ha.md) | Integration with orion-sentinel-dns-ha (Pi #1) |

## 🔒 Security Principles

1. **Passive Monitoring Only**: Pi #2 is NOT in the traffic path. No inline routing or IPS.
2. **No Direct DNS**: This repo consumes DNS logs from Pi #1; it does not run its own DNS.
3. **API-Based Enforcement**: Blocking happens via Pi-hole API on Pi #1, not locally.
4. **All Actions Logged**: Every AI decision and enforcement action is logged to Loki.
5. **Privacy-Focused**: All processing happens locally on your Pi; no cloud dependencies.

## 🧪 Key Features

- ✅ **Passive IDS**: Suricata on mirrored traffic (no network impact)
- ✅ **AI-Powered Detection**: Device anomaly & domain risk scoring on AI Hat
- ✅ **Threat Intelligence**: Real-time IOC feeds from AlienVault OTX, URLhaus, Feodo, PhishTank
- ✅ **Centralized Logging**: Loki stores NSM, DNS, and AI events
- ✅ **Visual Dashboards**: Grafana for real-time security visibility
- ✅ **Automated Response**: Policy-based domain blocking via Pi-hole
- ✅ **ARM-Optimized**: All services tuned for Raspberry Pi 5 (ARM64)
- ✅ **Extensible**: Easy to add new models, rules, or integrations

## 🔗 Related Projects

This repo is part of the **Orion Sentinel** ecosystem:

- **[orion-sentinel-dns-ha](https://github.com/yourusername/orion-sentinel-dns-ha)**: DNS & Privacy layer (Pi-hole + Unbound + HA) running on Pi #1
- **orion-sentinel-nsm-ai** (this repo): Network Security Monitoring & AI detection on Pi #2

## 📝 License

See [LICENSE](LICENSE) file.

## 🤝 Contributing

This is a personal home/lab project, but suggestions and improvements are welcome! Please open an issue or PR.

## ⚠️ Disclaimers

- This project is for educational and home/lab use
- No warranties or guarantees of security effectiveness
- Always test in a non-production environment first
- AI models require training data specific to your network for best results

---

**Built with ❤️ for privacy-focused home network security**

# Orion Sentinel - Network Security Monitoring & AI

**Mini-SOC Platform for Home/Lab Environments**

Orion Sentinel is a comprehensive security monitoring platform combining network security monitoring (NSM), AI-powered anomaly detection, automated response, and device management capabilities designed for home labs and small networks.

## Features

### 🛡️ SOAR-lite (Automated Response)
- Playbook-based automation
- Event-driven actions (blocking, tagging, notifications)
- Safety controls (dry-run mode, priorities)
- Integration with Pi-hole for DNS blocking
- **Web UI for playbook management** - [Guide](docs/web-ui.md)

### 📢 Multi-Channel Notifications
- **Email** (SMTP)
- **Signal** (via signal-cli)
- **Telegram** (Bot API)
- **Webhooks** (custom integrations)
- Rich alert formatting with threat context - [Setup Guide](docs/notifications.md)

### 🛡️ Threat Intelligence Integration
- **AlienVault OTX** - Community threat exchange
- **abuse.ch URLhaus** - Malicious URL tracking
- **abuse.ch Feodo Tracker** - Botnet C2 servers
- **PhishTank** - Verified phishing sites
- Automatic IOC enrichment and risk scoring - [Integration Guide](docs/threat-intel.md)

### 📊 Device Inventory & Fingerprinting
- Automatic device discovery
- Type classification (IoT, TV, NAS, etc.)
- Tagging and metadata management
- Risk scoring

### 🌐 Web Dashboard
- **Dashboard**: Health score and security overview
- **Events**: Searchable security event log with filters
- **Devices**: Complete asset inventory
- **Playbooks**: SOAR playbook management
- JSON REST APIs for all pages - [UI Guide](docs/web-ui.md)

### 🖥️ EDR-lite (Host Log Integration)
- Wazuh, osquery, syslog support
- Normalized event model
- Endpoint visibility

### 🍯 Honeypot Integration
- Designed for external honeypot containers
- High-confidence threat detection
- Attacker tracking

### 🔍 Change Detection
- Baseline snapshots
- Behavioral change alerts
- "What changed?" analysis

### 📈 Security Health Score
- Single 0-100 metric
- Four weighted components
- Actionable recommendations

### 🧪 Lab Mode
- Safe testing environment
- Device-based policy segregation
- Production protection

### 📊 Grafana Dashboards
- **SOC Management Dashboard**: Executive overview with health score, key metrics, and recent events
- **DNS & Pi-hole Dashboard**: DNS query analysis, block rates, and top domains
- Auto-provisioned on startup
- Real-time updates (30s refresh)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Grafana Dashboards                    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                        Loki (Logs)                           │
└─────────────────────────────────────────────────────────────┘
         ▲         ▲         ▲         ▲         ▲
         │         │         │         │         │
    ┌────┴───┐ ┌──┴───┐ ┌───┴────┐ ┌──┴─────┐ ┌┴────────┐
    │  SOAR  │ │Inven-│ │Change  │ │Health  │ │   API   │
    │Service │ │tory  │ │Monitor │ │Score   │ │ Server  │
    └────────┘ └──────┘ └────────┘ └────────┘ └─────────┘
         ▲                   ▲
         │                   │
    ┌────┴─────────────────────────────────────┐
    │  Event Sources (Suricata, DNS, AI, etc.) │
    └──────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9+ (for development)
- Loki instance (included in docker-compose)

### Installation

1. **Clone repository**:
   ```bash
   git clone https://github.com/yorgosroussakis/Orion-sentinel-netsec-ai.git
   cd Orion-sentinel-netsec-ai
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings (notifications, threat intel, Pi-hole, etc.)
   ```

3. **Configure playbooks** (optional):
   ```bash
   # Playbooks come with sensible defaults
   # Edit if you need custom automation
   nano stacks/ai/config/playbooks.yml
   ```

4. **Start services**:
   ```bash
   cd stacks/ai
   docker-compose up -d
   ```

5. **Initialize threat intelligence** (optional):
   ```bash
   # Fetch latest threat intel IOCs
   docker-compose exec ai-service python -m orion_ai.threat_intel.sync --hours 168
   ```

6. **Access interfaces**:
   - **Web UI**: http://localhost:8080 (Dashboard, Events, Devices, Playbooks)
   - **Grafana**: http://localhost:3000 (Analytics & Dashboards)
   - **API Docs**: http://localhost:8080/docs (OpenAPI/Swagger)

### Development Setup

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .

# Run a service
python -m orion_ai.soar.service
python -m orion_ai.inventory.service
python -m orion_ai.health_score.service
```

## Configuration

All configuration is via environment variables in `.env` file. See [.env.example](.env.example) for all options.

### Key Settings

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

### Core Features
- [SOAR Playbooks](docs/soar.md)
- [Notifications & Alerts](docs/notifications.md) 📢 **NEW**
- [Threat Intelligence](docs/threat-intel.md) 🛡️ **NEW**
- [Web Dashboard](docs/web-ui.md) 🌐 **NEW**
- [Device Inventory](docs/inventory.md)
- [Change Monitor](docs/change-monitor.md)
- [Health Score](docs/health-score.md)

### Additional
- [Lab Mode](docs/lab-mode.md)
- [Host Logs (EDR-lite)](docs/host-logs.md)
- [Honeypot Integration](src/orion_ai/honeypot/design.md)
- [Grafana Dashboards](config/grafana/README.md)

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

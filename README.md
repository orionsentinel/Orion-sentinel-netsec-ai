# Orion Sentinel - Network Security Monitoring & AI

**Mini-SOC Platform for Home/Lab Environments**

Orion Sentinel is a comprehensive security monitoring platform combining network security monitoring (NSM), AI-powered anomaly detection, automated response, and device management capabilities designed for home labs and small networks.

## Features

### 🛡️ SOAR-lite (Automated Response)
- Playbook-based automation
- Event-driven actions (blocking, tagging, notifications)
- Safety controls (dry-run mode, priorities)
- Integration with Pi-hole for DNS blocking

### 📊 Device Inventory & Fingerprinting
- Automatic device discovery
- Type classification (IoT, TV, NAS, etc.)
- Tagging and metadata management
- Risk scoring

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

### 🌐 REST API
- Device profile endpoints
- Natural language assistant (pattern-based)
- Timeline views

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

2. **Configure playbooks**:
   ```bash
   cp config/playbooks.yml.example config/playbooks.yml
   # Edit playbooks.yml for your environment
   ```

3. **Set environment variables**:
   ```bash
   export PIHOLE_API_KEY="your-api-key"
   export GRAFANA_ADMIN_PASSWORD="secure-password"
   ```

4. **Start services**:
   ```bash
   cd stacks/ai
   docker-compose up -d
   ```

5. **Access interfaces**:
   - Grafana: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

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

### SOAR Service

Key environment variables:

- `SOAR_DRY_RUN=1`: Enable dry run mode (recommended initially)
- `SOAR_POLL_INTERVAL=60`: Polling interval in seconds
- `SOAR_PLAYBOOKS_FILE=/config/playbooks.yml`: Playbook configuration
- `PIHOLE_URL=http://192.168.1.2`: Pi-hole instance URL
- `PIHOLE_API_KEY=xxx`: Pi-hole API key

### Inventory Service

- `INVENTORY_POLL_INTERVAL=300`: Update interval in seconds
- `INVENTORY_DB_PATH=/data/inventory.db`: SQLite database path

### Other Services

- `LOKI_URL=http://loki:3100`: Loki instance URL
- `LOG_LEVEL=INFO`: Logging level

See individual service documentation for details.

## Documentation

- [SOAR Playbooks](docs/soar.md)
- [Device Inventory](docs/inventory.md)
- [Change Monitor](docs/change-monitor.md)
- [Health Score](docs/health-score.md)
- [Lab Mode](docs/lab-mode.md)
- [Host Logs (EDR-lite)](docs/host-logs.md)
- [Honeypot Integration](src/orion_ai/honeypot/design.md)
- [Grafana Dashboards](config/grafana/README.md)

## Module Structure

```
src/orion_ai/
├── soar/              # SOAR automation
│   ├── models.py      # Data models
│   ├── engine.py      # Playbook engine
│   ├── actions.py     # Action executors
│   └── service.py     # SOAR service
├── inventory/         # Device inventory
│   ├── models.py
│   ├── collector.py   # Log collection
│   ├── fingerprinting.py
│   ├── store.py       # SQLite storage
│   └── service.py
├── host_logs/         # EDR-lite
│   ├── models.py
│   └── normalizer.py  # Log normalization
├── honeypot/          # Honeypot integration
│   └── design.md
├── change_monitor/    # Change detection
│   ├── models.py
│   ├── baseline.py
│   ├── analyzer.py
│   └── service.py
├── health_score/      # Security health score
│   ├── models.py
│   ├── calculator.py
│   └── service.py
└── ui/                # REST APIs
    ├── device_profile_api.py
    ├── assistant_api.py
    └── http_server.py
```

## API Examples

### Get Device Profile

```bash
curl http://localhost:8000/device/192.168.1.50
```

### Get Device Timeline

```bash
curl http://localhost:8000/device/192.168.1.50/timeline?hours=24
```

### Tag a Device

```bash
curl -X POST http://localhost:8000/device/192.168.1.50/tag?tag=lab
```

### Query Assistant

```bash
curl -X POST http://localhost:8000/assistant/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me suspicious activity from 192.168.1.50"}'
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

- [ ] Complete Loki integration (query & push)
- [ ] Pi-hole API client implementation
- [ ] Notification channels (Signal, Telegram, Email)
- [ ] Grafana dashboard templates
- [ ] AI model integration (ONNX/TFLite)
- [ ] Threat intel feed integration (abuse.ch, OTX)
- [ ] Template variable resolution in playbooks
- [ ] Web UI for playbook management
- [ ] MITRE ATT&CK mapping

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

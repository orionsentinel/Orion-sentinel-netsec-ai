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
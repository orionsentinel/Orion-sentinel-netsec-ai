# Orion Sentinel - NetSec Node

**Production-Ready Network Security Monitoring for Raspberry Pi 5 + NVMe HAT**

Orion Sentinel NetSec is a network security sensor designed for home labs and small networks. This repository contains the **NetSec Pi** - a passive IDS sensor running Suricata on a Raspberry Pi 5 with NVMe storage, integrated with the broader **Orion Sentinel** ecosystem.

## 🎯 What is This?

**NetSec Pi** runs on Raspberry Pi 5 + NVMe HAT as a passive network security sensor:

- ✅ **Passive monitoring** - No inline blocking, zero network disruption
- ✅ **NVMe-backed storage** - Fast, reliable logging without microSD wear
- ✅ **CoreSrv integration** - Ships logs/metrics to centralized observability stack  
- ✅ **Production-ready** - Stable, minimal, well-documented deployment

## 📋 Hardware Requirements

**Required:**
- Raspberry Pi 5 (4GB minimum, 8GB recommended)
- **NVMe HAT** with M.2 NVMe SSD (128GB minimum, 256GB+ recommended)
- MicroSD card (16GB+ for OS boot)
- Network switch with port mirroring (SPAN) capability
- Ethernet cable (dedicated interface for mirrored traffic recommended)

**Optional:**
- USB Ethernet adapter (for dedicated capture interface)
- Active cooling (fan or heatsink for sustained loads)

**Why NVMe?**
- MicroSD cards wear out quickly with continuous logging
- NVMe provides high-speed I/O for traffic analysis
- Reliable storage for 24/7 operation

See **[docs/architecture-netsec.md](docs/architecture-netsec.md)** for detailed setup.

## 🏗️ Architecture - Orion Sentinel Ecosystem

The Orion Sentinel ecosystem consists of three nodes:

### 1. NetSec Pi (This Repository) - Network Sensor
- Runs Suricata IDS on mirrored switch traffic
- Stores logs and PCAPs on NVMe (/mnt/orion-nvme-netsec)
- Ships logs to CoreSrv Loki via Promtail
- Exports metrics for CoreSrv Prometheus (port 9100)
- Optional: Local EveBox UI for alert browsing

### 2. CoreSrv (Separate Repository) - Observability
- **Loki** - Central log aggregation for all Orion nodes
- **Grafana** - Dashboards and visualization
- **Prometheus** - Metrics collection and alerting
- **Uptime Kuma** - Service monitoring
- Repository: [Orion-Sentinel-CoreSrv](https://github.com/orionsentinel/Orion-Sentinel-CoreSrv)

### 3. AI Node (Future) - Optional AI Inference
- Status: Documented but NOT required for v1
- Hardware: Separate Pi 5 + AI HAT (not on NetSec Pi)
- Purpose: AI-powered threat detection and log enrichment
- See [docs/ai-node-future.md](docs/ai-node-future.md)

```
┌─────────────────────────────────────────────────────────────┐
│              CoreSrv (Separate Server/PC)                   │
│  • Loki (central logs)  • Grafana (dashboards)              │
│  • Prometheus (metrics) • Uptime Kuma (monitoring)          │
└──────────────────────▲──────────────────────────────────────┘
                       │ Logs & Metrics
                       │
┌──────────────────────┴──────────────────────────────────────┐
│             NetSec Pi (This Repository)                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Raspberry Pi 5 + NVMe HAT                              │ │
│  │ • Suricata IDS (passive capture)                       │ │
│  │ • Promtail (log shipping)                              │ │
│  │ • Node Exporter (metrics)                              │ │
│  │ • NVMe: /mnt/orion-nvme-netsec (logs, PCAPs)           │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────▲──────────────────────────────────────────┘
                    │ Port Mirror/SPAN
                    │
            ┌───────┴────────┐
            │ Network Switch │
            └────────────────┘
```

**Detailed docs:** [docs/architecture-netsec.md](docs/architecture-netsec.md)

## 🚀 Quick Start (Production - NVMe Deployment)

### 1. Clone Repository

```bash
git clone https://github.com/orionsentinel/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai
```

### 2. Prepare NVMe Storage

**Mount NVMe (one-time):**

```bash
# Format NVMe (⚠️ ERASES DATA!)
sudo mkfs.ext4 /dev/nvme0n1p1

# Create and mount
sudo mkdir -p /mnt/orion-nvme-netsec
sudo mount /dev/nvme0n1p1 /mnt/orion-nvme-netsec

# Add to /etc/fstab for auto-mount on boot
echo "UUID=$(sudo blkid -s UUID -o value /dev/nvme0n1p1)  /mnt/orion-nvme-netsec  ext4  defaults,noatime  0  2" | sudo tee -a /etc/fstab

# Test
sudo mount -a
```

**Verify NVMe setup:**

```bash
./scripts/check-nvme.sh
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Key settings:**

```bash
# Network interface for mirrored traffic (verify with: ip link show)
NETSEC_INTERFACE=eth0

# CoreSrv Loki endpoint
LOKI_URL=http://192.168.x.x:3100  # Replace with CoreSrv IP

# Node identification
ORION_NODE_NAME=netsec-pi-01
```

### 4. Start Services

**Production (recommended):**

```bash
docker compose --profile netsec-minimal up -d
```

**With local EveBox UI:**

```bash
docker compose --profile netsec-plus-evebox up -d
# Access: http://netsec-pi-ip:5636
```

### 5. Verify Deployment

```bash
# Check services
docker compose ps

# Verify Suricata capture
docker logs orion-netsec-suricata | grep -i "received"

# Verify log shipping
docker logs orion-netsec-promtail | grep "POST"

# Check NVMe
./scripts/check-nvme.sh
```

**Generate test alert:**

```bash
curl https://testmyids.com
docker exec orion-netsec-suricata tail /var/log/suricata/eve.json | jq 'select(.event_type=="alert")'
```

## 🔧 Docker Compose Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| **netsec-minimal** | Suricata + Promtail + Node Exporter | Production sensor (default) |
| **netsec-plus-evebox** | Minimal + EveBox UI | Production + local alert browsing |
| **netsec-debug** | Debug toolbox (tcpdump, etc.) | Network troubleshooting |
| **ai** (legacy) | AI services (SOAR, Inventory) | Legacy mode (not recommended) |

**Start commands:**

```bash
# Production minimal
docker compose --profile netsec-minimal up -d

# With EveBox
docker compose --profile netsec-plus-evebox up -d

# With debug tools
docker compose --profile netsec-minimal --profile netsec-debug up -d
docker exec -it orion-netsec-debug tcpdump -i eth0 -nn
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[docs/architecture-netsec.md](docs/architecture-netsec.md)** | Detailed architecture, NVMe setup, data flows |
| **[docs/grafana-dashboards.md](docs/grafana-dashboards.md)** | Grafana dashboards for CoreSrv |
| **[docs/ai-node-future.md](docs/ai-node-future.md)** | Future AI node architecture (v2) |
| **[.env.example](.env.example)** | Environment variable reference |

### Legacy Documentation (AI Services)
- [docs/soar.md](docs/soar.md) - SOAR playbooks
- [docs/threat-intel.md](docs/threat-intel.md) - Threat intelligence
- [docs/notifications.md](docs/notifications.md) - Alert notifications

## 🔐 Security

**Container Security:**
- Suricata: Minimal capabilities (NET_ADMIN, NET_RAW only)
- Promtail: Read-only log access
- No containers run as root unnecessarily

**Host Security:**
```bash
# Firewall (ufw) - Allow only required ports
sudo ufw allow from 192.168.0.0/16 to any port 22    # SSH from LAN
sudo ufw allow from <coresrv-ip> to any port 9100    # Prometheus metrics
sudo ufw allow from 192.168.0.0/16 to any port 5636  # EveBox (optional)
sudo ufw enable
```

**Network Security:**
- NetSec Pi should NEVER be exposed to internet
- Use VPN for remote access
- All services bind to LAN only

## 🆘 Troubleshooting

**Suricata not capturing:**
```bash
# Check interface
docker logs orion-netsec-suricata | grep "Using AF_PACKET"

# Verify SPAN on switch
sudo tcpdump -i eth0 -c 10  # Should see mirrored traffic
```

**Promtail not shipping:**
```bash
# Check Loki connectivity
docker exec orion-netsec-promtail wget -O- http://192.168.x.x:3100/ready

# Check logs
docker logs orion-netsec-promtail | grep -i error
```

**NVMe issues:**
```bash
# Check mount
df -h /mnt/orion-nvme-netsec

# Check permissions
ls -la /mnt/orion-nvme-netsec/suricata/

# Run health check
./scripts/check-nvme.sh
```

---

## Legacy README Content (AI Services)

> **Note:** The sections below describe legacy AI services that run ON the NetSec Pi.  
> For production deployments, these are optional and not recommended.  
> Future AI capabilities will run on a separate AI Node (see docs/ai-node-future.md).

---

## 🚀 Quick Install (Legacy - With AI Services)

> ⚠️ **For production, use the Quick Start section above instead**

```bash
git clone https://github.com/orionsentinel/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai
./setup.sh  # Interactive setup - guides you through everything
make start-spog  # Start in production mode (or make start-standalone for dev)
```

See [Quick Start](#quick-start) section below for detailed instructions.

## 🏗️ Architecture

### Deployment Modes

Orion Sentinel supports two deployment modes:

#### **SPoG Mode (Single Pane of Glass) - Recommended**
NetSec Pi acts as a sensor feeding into centralized CoreSrv for observability.

```
┌──────────────────────────────────────────────────────────┐
│                  CoreSrv (Dell) - SPoG                   │
│  • Loki (central log aggregation)                        │
│  • Prometheus (metrics collection)                       │
│  • Grafana (all dashboards)                              │
│  • Traefik (reverse proxy for Web UI)                    │
└────────────────────────▲─────────────────────────────────┘
                         │ Logs & Metrics
                         │
┌────────────────────────┴─────────────────────────────────┐
│           NetSec Node (Pi 5) - This Repository           │
│  • Suricata IDS (passive monitoring)                     │
│  • AI threat detection & correlation                     │
│  • SOAR automation                                       │
│  • Promtail (ships logs to CoreSrv)                      │
│  • Web UI (exposed via CoreSrv Traefik)                  │
└──────────────────────────────────────────────────────────┘
         ▲
         │ Port Mirror / SPAN
         │
┌────────┴────────┐
│  Router/Switch  │
└─────────────────┘
```

**Configure**: Set `LOKI_URL=http://<CoreSrv-IP>:3100` in `.env`

---

#### **Standalone Mode - For Development/Testing**
NetSec Pi runs its own Loki + Grafana for isolated operation.

**Configure**: Set `LOCAL_OBSERVABILITY=true` in `.env`

**Access**: 
- Grafana: `http://localhost:3000`
- Web UI: `http://localhost:8000`

---

### Component Architecture

The NetSec Node consists of layered services managed via Docker Compose profiles:

**Profile: netsec-core** (Core NSM)
- Suricata IDS (packet analysis)
- Promtail (log shipping)
- Node Exporter (system metrics)

**Profile: ai** (AI Detection & Response)
- SOAR service (automated playbooks)
- Inventory service (device tracking)
- Change Monitor (anomaly detection)
- Health Score (security posture)
- Web API/UI (dashboard)

**Profile: exporters** (Optional Metrics)
- Additional system metrics exporters

**Start modes**:
```bash
make up-core         # Core NSM only
make up-all          # Core + AI (recommended)
```

For detailed architecture, see [PLAN.md](PLAN.md).

---

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
- **Hardware acceleration**: Optional support for Raspberry Pi AI Hat (Hailo-8, ~13 TOPS)
  - CPU fallback available for systems without accelerator
  - See [docs/ai-accelerator.md](docs/ai-accelerator.md) for setup
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

### Installation

#### Method 1: Automated Bootstrap (Recommended)

The bootstrap script handles all prerequisites and configuration:

```bash
# 1. Clone repository
git clone https://github.com/orionsentinel/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai

# 2. Run bootstrap
./scripts/bootstrap-netsec.sh

# The bootstrap script will:
# ✓ Check Docker and Docker Compose installation
# ✓ Validate network interface exists
# ✓ Set kernel parameters if needed
# ✓ Create .env file from template with guided prompts
# ✓ Show you next steps

# 3. Start services
make up-all
```

**What you'll configure**:
- `MONITOR_IF` - Network interface receiving mirrored traffic (e.g., eth0)
- `LOKI_URL` - CoreSrv Loki endpoint (SPoG mode) or local Loki
- `NODE_NAME` - Identifier for this sensor node

---

#### Method 2: Manual Setup

If you prefer manual configuration:

**1. Clone repository**:
```bash
git clone https://github.com/orionsentinel/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai
```

**2. Create .env file**:
```bash
cp .env.example .env
nano .env
```

**3. Configure key variables**:
```bash
# Network interface for Suricata (required)
MONITOR_IF=eth0

# CoreSrv Loki URL (for SPoG mode)
LOKI_URL=http://192.168.8.50:3100

# Or use local Loki (standalone mode)
# LOKI_URL=http://loki:3100
# LOCAL_OBSERVABILITY=true

# Node identification
NODE_NAME=netsec-pi-01
```

**4. Start services**:
```bash
docker compose --profile netsec-core --profile ai up -d
# or use: make up-all
```

---

### Validation

After deployment, verify everything is working:

```bash
# Run automated validation
make test
```

**Manual checks**:

1. **Services running**:
   ```bash
   make status
   # All services should show "Up"
   ```

2. **Suricata capturing traffic**:
   ```bash
   docker logs orion-suricata | grep "Capture"
   # Should show: "Received N packets"
   ```

3. **Promtail shipping logs**:
   ```bash
   docker logs orion-promtail | grep "POST"
   # Should show: "POST /loki/api/v1/push (200 OK)"
   ```

4. **Web UI accessible**:
   ```bash
   curl http://localhost:8000/api/health
   # Should return: {"status": "healthy"}
   ```

5. **Generate test alert**:
   ```bash
   # From another device
   curl https://testmyids.com
   
   # Check for alert
   docker exec orion-suricata tail /var/log/suricata/eve.json | jq 'select(.event_type=="alert")'
   ```

For comprehensive validation steps, see [docs/validation.md](docs/validation.md).

---

### Network Configuration

**IMPORTANT**: Your network switch must be configured for port mirroring (SPAN).

**Quick Setup**:
1. Identify uplink port on switch (usually Port 1)
2. Identify NetSec Pi port (e.g., Port 24)
3. Configure port mirror: Source = uplink, Destination = Pi port, Direction = Both

**Vendor-specific guides** available in [docs/network-config.md](docs/network-config.md) for:
- UniFi
- Cisco Catalyst
- TP-Link
- Netgear
- MikroTik

---

#### SPoG Mode (Production - Recommended)

Deploy NetSec as a sensor that reports to CoreSrv:

1. **Clone repository**:
   ```bash
   git clone https://github.com/orionsentinel/Orion-sentinel-netsec-ai.git
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
make up-core            # Start core NSM services only
make up-all             # Start all services (core + AI) - RECOMMENDED
make stop               # Stop all services
make restart            # Restart all services
make status             # Check service status
make logs               # View logs (live tail)

# Setup & validation
make bootstrap          # Initial system setup (checks Docker, creates .env)
make test               # Run validation tests
make verify-spog        # Verify CoreSrv connectivity (SPoG mode)

# Maintenance
make update-images      # Pull latest Docker images
make backup-config      # Backup .env and config files
make clean              # Clean up containers and temp files

# Development
make dev-install        # Set up Python development environment
make test-python        # Run Python unit tests
make lint               # Run linters
```

#### Using Docker Compose Directly

```bash
# Start services with specific profiles
docker compose --profile netsec-core up -d                    # Core only
docker compose --profile netsec-core --profile ai up -d       # Full stack
docker compose --profile netsec-core --profile exporters up -d # Core + metrics

# Stop services
docker compose down

# View logs
docker compose logs -f suricata
docker compose logs -f --tail=100

# Check status
docker compose ps
```

#### Legacy netsecctl.sh Script

The legacy script still works for SPoG/Standalone modes:

```bash
# Check service status
./scripts/netsecctl.sh status

# View logs
./scripts/netsecctl.sh logs

# Stop all services
./scripts/netsecctl.sh down

# Start in SPoG mode (legacy)
./scripts/netsecctl.sh up-spog

# Start in Standalone mode (legacy)
./scripts/netsecctl.sh up-standalone
```

---

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

**Network Interface** (required):
- `MONITOR_IF` - Interface receiving mirrored traffic (e.g., `eth0`, `enx00e04c68xxxx`)

**Node Identification** (recommended):
- `NODE_NAME` - Unique identifier for this sensor (e.g., `netsec-pi-01`)
- `NODE_LOCATION` - Physical location (e.g., `basement`, `home-lab`)
- `HOSTNAME` - System hostname for proper log labeling

**Loki Connection** (SPoG Integration):
- `LOKI_URL` - CoreSrv Loki URL (e.g., `http://192.168.8.50:3100`)
- `PROMETHEUS_URL` - CoreSrv Prometheus URL (e.g., `http://192.168.8.50:9090`)
- `LOCAL_OBSERVABILITY` - Enable local Loki+Grafana (`true`/`false`)

**SOAR Automation**:
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

### 📘 Getting Started
- **[PLAN.md](PLAN.md)** - Architecture, profiles, and deployment guide
- **[QUICKSTART.md](QUICKSTART.md)** - Fast setup guide
- **[docs/validation.md](docs/validation.md)** - Testing and validation procedures

### 🔧 Configuration & Setup
- **[docs/network-config.md](docs/network-config.md)** - Port mirroring & firewall setup
- **[docs/ai-accelerator.md](docs/ai-accelerator.md)** - AI Hat installation & config
- **[.env.example](.env.example)** - Environment variable reference

### 📊 Observability
- **[grafana_dashboards/](grafana_dashboards/)** - Pre-built Grafana dashboards
- **[docs/CORESRV-INTEGRATION.md](docs/CORESRV-INTEGRATION.md)** - CoreSrv SPoG setup
- **[docs/CORESRV-DASHBOARDS.md](docs/CORESRV-DASHBOARDS.md)** - Dashboard export guide

### 🚨 Features & Operations
- **[docs/soar.md](docs/soar.md)** - SOAR playbooks and automation
- **[docs/notifications.md](docs/notifications.md)** - Alert configuration
- **[docs/threat-intel.md](docs/threat-intel.md)** - Threat intelligence feeds
- **[docs/web-ui.md](docs/web-ui.md)** - Web dashboard usage
- **[docs/inventory.md](docs/inventory.md)** - Device inventory management
- **[docs/health-score.md](docs/health-score.md)** - Security health scoring
- **[docs/change-monitor.md](docs/change-monitor.md)** - Change detection

### 🏗️ Architecture & Stacks
- **[stacks/nsm/README.md](stacks/nsm/README.md)** - NSM stack details
- **[stacks/ai/README.md](stacks/ai/README.md)** - AI stack details
- **[docs/architecture.md](docs/architecture.md)** - System design (legacy)

### 🛠️ Advanced Topics
- **[docs/lab-mode.md](docs/lab-mode.md)** - Safe testing mode
- **[docs/host-logs.md](docs/host-logs.md)** - EDR-lite integration
- **[src/orion_ai/honeypot/design.md](src/orion_ai/honeypot/design.md)** - Honeypot integration

---

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
- [ ] Backup system configured and tested

## 🗄️ Backup & Restore

Orion Sentinel includes comprehensive backup and restore capabilities for all critical data.

### Quick Backup

```bash
# Backup all critical volumes
sudo ./backup/backup-volumes.sh
```

Default backup location: `/srv/backups/orion/YYYY-MM-DD_HH-MM-SS`

### Quick Restore

```bash
# Stop services
make down

# Restore a specific volume
sudo ./backup/restore-volume.sh /srv/backups/orion/2024-01-15/VOLUME_NAME.tar.gz

# Restart services
make up-all
```

### Critical Volumes

The backup system protects these essential volumes:

| Volume | Description | Priority |
|--------|-------------|----------|
| `suricata-logs` | IDS logs and alerts | High |
| `suricata-rules` | Detection rules and config | High |
| `inventory-data` | Device inventory database | High |
| `soar-data` | Playbook execution history | Medium |
| `change-data` | Network change monitoring | Medium |
| `health-data` | Security health scores | Low |

### Automated Backup Setup

For production deployments, set up automated weekly backups:

```bash
# Create backup directory
sudo mkdir -p /srv/backups/orion

# Add to crontab (runs every Sunday at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * 0 $(pwd)/backup/backup-volumes.sh") | crontab -
```

### Backup Best Practices

1. **Test your backups regularly** - Restore to a test environment monthly
2. **Keep multiple versions** - Maintain 7 daily, 4 weekly, 6 monthly backups
3. **Store offsite** - Copy backups to external drive or remote server
4. **Monitor backup success** - Check backup logs and manifest files
5. **Document restore procedures** - Keep team informed of recovery process

For detailed backup/restore procedures, see [backup/README.md](backup/README.md)

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
6. **Service Isolation**: No services exposed directly to the internet - all access via Traefik+Authelia on CoreSrv.
7. **Pinned Images**: Docker images pinned to specific versions for security and reproducibility.
8. **Regular Updates**: Security patches applied promptly via documented update procedures.

### Security Best Practices

#### Service Exposure
- **SPoG Mode (Production)**: Web UI exposed only via CoreSrv Traefik with Authelia authentication
- **Standalone Mode (Lab)**: Services bound to localhost or LAN only
- **Never expose directly**: Do not expose Grafana, Loki, or API ports to the internet without authentication

#### Port Security
The following ports are used internally and should NOT be exposed to the internet:
- `8000` - API/Web UI (access via Traefik on CoreSrv)
- `3100` - Loki (internal log aggregation)
- `9100` - Node Exporter (metrics, LAN only)

#### Update Strategy
See [docs/update.md](docs/update.md) for:
- Security patch procedures
- Version pinning strategy  
- Update testing workflow
- Rollback procedures

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

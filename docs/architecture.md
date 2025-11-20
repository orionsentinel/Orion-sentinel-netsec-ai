# Architecture

This document describes the detailed architecture of the Orion Sentinel NSM + AI system running on Pi #2 (Security Pi).

## System Overview

The Orion Sentinel project consists of two physically separate Raspberry Pi systems:

1. **Pi #1 (DNS Pi)** - Runs `orion-sentinel-dns-ha`
   - Pi-hole for ad/malware blocking
   - Unbound for recursive DNS resolution
   - Keepalived for high availability
   - Exposes DNS logs and Pi-hole API

2. **Pi #2 (Security Pi)** - Runs `orion-sentinel-nsm-ai` (THIS REPO)
   - Passive network security monitoring
   - AI-powered threat detection
   - Centralized logging and visualization
   - Optional automated response via Pi-hole API

## Pi #2 Components

### Network Security Monitoring Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        Pi #2 (Security Pi)                      │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │   Suricata   │────▶│   Promtail   │────▶│     Loki     │  │
│  │              │     │              │     │              │  │
│  │ - IDS        │     │ - Log        │     │ - Log Store  │  │
│  │ - Passive    │     │   Shipper    │     │ - Indexing   │  │
│  │ - AF_PACKET  │     │              │     │              │  │
│  └──────────────┘     └──────────────┘     └──────┬───────┘  │
│         ▲                                          │          │
│         │                                          │          │
│         │ Mirrored                                 │          │
│         │ Traffic                                  ▼          │
│         │                                   ┌──────────────┐  │
│  ┌──────┴──────┐                           │   Grafana    │  │
│  │  eth0/eth1  │                           │              │  │
│  │  (Mirror    │                           │ - Dashboards │  │
│  │   Port)     │                           │ - Queries    │  │
│  └─────────────┘                           └──────────────┘  │
│                                                                │
│  ┌──────────────┐     ┌──────────────┐                       │
│  │  AI Service  │────▶│   Promtail   │──────────┐            │
│  │              │     │              │          │            │
│  │ - Device     │     │ - AI Result  │          │            │
│  │   Anomaly    │     │   Shipper    │          ▼            │
│  │ - Domain     │     └──────────────┘     (to Loki)         │
│  │   Risk       │                                            │
│  │ - Models     │◀───── Reads NSM + DNS logs from Loki       │
│  └──────┬───────┘                                            │
│         │                                                     │
│         │ Calls API                                          │
│         ▼                                                     │
│  ┌─────────────────────────────────────────┐                │
│  │  Pi-hole API Client (calls Pi #1)       │                │
│  │  - Adds/removes domains from blocklist  │                │
│  └─────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flows

#### 1. Network Traffic Flow
```
Router/Switch → Port Mirror → Pi #2 eth0/eth1 → Suricata (IDS) → eve.json → Promtail → Loki
```

- Router/switch is configured to mirror **all** LAN traffic to Pi #2's dedicated interface
- Suricata runs in **passive mode** (no inline blocking)
- Uses AF_PACKET for efficient packet capture on ARM
- Outputs JSON events (eve.json) containing:
  - Alerts (signature matches)
  - Flow records (connections)
  - DNS queries/responses
  - HTTP/TLS metadata
  - File transfers

#### 2. DNS Log Flow (from Pi #1)
```
Pi #1: Pi-hole/Unbound → Promtail → HTTP → Pi #2: Loki
```

- Pi #1 runs Promtail locally (configured in `orion-sentinel-dns-ha` repo)
- Ships Pi-hole and Unbound logs to Pi #2's Loki HTTP endpoint (port 3100)
- Labels applied:
  - `service="pihole"` or `service="unbound"`
  - `pi="pi1-dns"`
  - `log_type="dns"`

#### 3. AI Detection Flow
```
Loki → AI Service → Feature Extraction → Model Inference → Results → Loki
                                                          ↓
                                                     Pi-hole API
```

- AI service periodically queries Loki for NSM + DNS events (e.g., every 5-15 minutes)
- Two parallel pipelines:
  1. **Device Anomaly Detection**:
     - Groups events by source IP and time window
     - Extracts behavioral features (connection count, bytes, DNS patterns)
     - Runs ONNX/TFLite model on AI Hat
     - Outputs anomaly score per device
  2. **Domain Risk Scoring**:
     - Extracts unique domains from DNS logs
     - Computes domain features (length, entropy, TLD, character distribution)
     - Runs DGA/phishing detection model
     - Outputs risk score per domain
- Results written as structured JSON logs → Promtail → Loki
- High-risk domains (score > threshold) → Pi-hole API call to block

#### 4. Visualization Flow
```
Grafana → LogQL queries → Loki → Returns matched logs → Grafana renders dashboards
```

## Component Details

### Suricata (IDS)

**Role**: Passive network intrusion detection

**Configuration**:
- Mode: `af-packet` (efficient on ARM)
- Interface: Configurable via `NSM_IFACE` env var
- Rules: Emerging Threats Open ruleset (auto-updated)
- Output: JSON eve.json with:
  - `alert`: Signature-based alerts
  - `flow`: Connection metadata
  - `dns`: DNS queries/responses
  - `http`: HTTP requests/responses
  - `tls`: TLS handshakes and certificates
  - `fileinfo`: File transfers

**Resource Tuning for Pi 5**:
- Limited to 2-4 CPU cores
- Memory capped at 2 GB
- Ring buffer size reduced for ARM

**Key Files**:
- `stacks/nsm/suricata/suricata.yaml`: Main configuration
- `/var/log/suricata/eve.json`: JSON event output

### Loki (Log Aggregation)

**Role**: Centralized log storage and indexing

**Data Sources**:
- Suricata eve.json (via Promtail)
- AI service results (via Promtail)
- Pi-hole logs from Pi #1 (via Promtail on Pi #1)
- Unbound logs from Pi #1 (via Promtail on Pi #1)

**Configuration**:
- Retention: 7-14 days (configurable based on disk space)
- Compaction: Enabled for efficiency
- Storage: Local filesystem on Pi #2
- Chunk target size: 512 KB (optimized for small-scale)

**Label Strategy**:
```yaml
Labels:
  - service: suricata, pihole, unbound, ai-device-anomaly, ai-domain-risk
  - pi: pi1-dns, pi2-security
  - log_type: nsm, dns, ai
  - severity: info, warning, critical (for AI events)
```

**Endpoints**:
- HTTP API: `http://localhost:3100`
- Health: `http://localhost:3100/ready`

### Promtail (Log Shipper)

**Role**: Ship logs from files to Loki

**Instances**:
1. **On Pi #2**: Ships Suricata + AI logs
2. **On Pi #1** (configured in `orion-sentinel-dns-ha`): Ships DNS logs

**Configuration** (Pi #2):
```yaml
scrape_configs:
  - job_name: suricata
    static_configs:
      - targets: [localhost]
        labels:
          service: suricata
          pi: pi2-security
          log_type: nsm
    pipeline_stages:
      - json:
          expressions:
            event_type: event_type
      - labels:
          event_type:
  
  - job_name: ai-results
    static_configs:
      - targets: [localhost]
        labels:
          service: ai
          pi: pi2-security
          log_type: ai
```

### Grafana (Visualization)

**Role**: Dashboards and log exploration

**Datasources**:
- Loki (primary): All logs from NSM, DNS, and AI

**Key Dashboards** (to be created):
1. **Network Overview**:
   - Top talkers (by bytes, connections)
   - Protocol distribution
   - Geographic distribution (if GeoIP enabled)

2. **Security Alerts**:
   - Suricata alerts by severity
   - Alert timeline
   - Top alert signatures

3. **DNS Analytics**:
   - Top queried domains
   - Query volume over time
   - Blocked queries (from Pi-hole)

4. **AI Detection**:
   - Device anomaly scores
   - High-risk domains detected
   - Enforcement actions (domains blocked)

**Access**:
- URL: `http://pi2-ip:3000`
- Default credentials: `admin / admin` (change immediately!)

### AI Service

**Role**: ML-based anomaly detection and threat scoring

**Architecture**:
```
Python Application
├── Config (env vars)
├── Log Reader (Loki API client)
├── Feature Extractor (NSM + DNS → numerical features)
├── Model Runner (ONNX/TFLite inference on AI Hat)
├── Pipelines (orchestrate detection flows)
├── Output Writer (results → Loki)
├── Pi-hole Client (enforcement via API)
└── HTTP Server (optional API for status/results)
```

**Detection Pipelines**:

1. **Device Anomaly Detection**:
   - **Input**: NSM events for device X in time window [t0, t1]
   - **Features** (per device):
     - Total connections (in/out)
     - Bytes sent/received
     - Unique destination IPs/ports
     - DNS query count
     - Unique domains queried
     - Protocol distribution (TCP/UDP/ICMP)
     - Average packet size
     - Connection duration stats
   - **Model**: ONNX autoencoder or isolation forest
   - **Output**: Anomaly score (0-1) per device

2. **Domain Risk Scoring**:
   - **Input**: Unique domains from DNS logs
   - **Features** (per domain):
     - Domain length
     - Subdomain count
     - Character entropy
     - Vowel/consonant ratio
     - TLD category (common vs rare)
     - Lexical similarity to known DGA patterns
     - WHOIS age (if available)
   - **Model**: ONNX/TFLite classifier (DGA, phishing, benign)
   - **Output**: Risk score (0-1) per domain

**Execution Model**:
- Batch processing every N minutes (configurable, default: 10 min)
- Or triggered via HTTP API
- Writes results as JSON logs → Loki

**Enforcement Policy**:
```python
if domain_risk_score >= RISK_THRESHOLD (e.g., 0.85):
    action = "BLOCK"
    pihole_client.add_domain(domain, comment=f"AI-detected: score={risk_score}")
    log_action(domain, risk_score, "BLOCK")
else:
    action = "ALLOW"
```

## Integration with Pi #1 (orion-sentinel-dns-ha)

### DNS Log Shipping

Pi #1 must run Promtail to ship logs to Pi #2:

**On Pi #1** (in `orion-sentinel-dns-ha` repo):
```yaml
# promtail-config.yml
clients:
  - url: http://<pi2-ip>:3100/loki/api/v1/push

scrape_configs:
  - job_name: pihole
    static_configs:
      - targets: [localhost]
        labels:
          service: pihole
          pi: pi1-dns
          log_type: dns
    pipeline_stages:
      - regex:
          expression: ...  # Parse Pi-hole log format

  - job_name: unbound
    static_configs:
      - targets: [localhost]
        labels:
          service: unbound
          pi: pi1-dns
          log_type: dns
```

**Required Configuration**:
- Firewall on Pi #2: Allow port 3100 from Pi #1
- DNS resolution: Pi #1 can resolve Pi #2's hostname or use static IP

### Pi-hole API Integration

**Endpoints Used** (on Pi #1):
- `POST /admin/api.php?list=black&add=<domain>&auth=<token>`: Add domain to blocklist
- `POST /admin/api.php?list=black&sub=<domain>&auth=<token>`: Remove domain from blocklist

**Configuration** (on Pi #2 AI service):
```bash
PIHOLE_API_URL=http://<pi1-ip>/admin/api.php
PIHOLE_API_TOKEN=<secret-token>
```

**Security**:
- API token should be stored securely (env var, not committed)
- All API calls logged for audit
- Rate limiting to prevent abuse

## Network Configuration

### Port Mirroring Setup

**Required**: Router or managed switch must support port mirroring (SPAN/TAP)

**Configuration Example** (varies by device):
```
Mirror Source: All LAN ports (or specific VLANs)
Mirror Destination: Pi #2's Ethernet port (e.g., eth1)
Direction: Both (ingress + egress)
```

**Verification**:
```bash
# On Pi #2, check for mirrored traffic
sudo tcpdump -i eth1 -c 100
```

### Firewall Rules (Pi #2)

**Inbound**:
- Port 3000 (Grafana): Allow from LAN
- Port 3100 (Loki): Allow from Pi #1's IP
- Port 8080 (AI API, optional): Allow from LAN

**Outbound**:
- Pi #1's Pi-hole API: Port 80/443
- Internet: For rule updates (Suricata)

## Resource Planning

### Pi 5 (8 GB) Resource Allocation

| Service      | CPU (cores) | RAM (MB) | Disk (GB) | Notes                          |
|--------------|-------------|----------|-----------|--------------------------------|
| Suricata     | 2-3         | 1500     | 1         | Passive mode, limited rulesets |
| Loki         | 1           | 1000     | 10-50     | Depends on retention period    |
| Promtail     | 0.5         | 200      | 0.1       | Lightweight                    |
| Grafana      | 1           | 400      | 1         | Dashboards only                |
| AI Service   | 2 (AI Hat)  | 1500     | 5         | Uses AI Hat for inference      |
| **Total**    | **6-7**     | **4600** | **17-57** | Fits on Pi 5 with headroom     |

**Storage Notes**:
- Use external SSD for Loki data (better performance and durability)
- Log rotation and retention policies critical for disk management
- AI models stored separately (not in Docker volumes)

## Security Considerations

1. **Passive Mode Only**:
   - Pi #2 does NOT route or forward packets
   - No inline blocking or filtering
   - Cannot disrupt network if it fails

2. **Sensitive Data**:
   - All DNS queries and flows are logged (privacy implications)
   - Logs should be encrypted at rest (optional for home use)
   - Access to Grafana should be authenticated

3. **AI Model Trust**:
   - Models should be from trusted sources or self-trained
   - Model files should be integrity-checked (checksums)
   - False positives: Review blocked domains periodically

4. **Pi-hole API Security**:
   - API token must be kept secret
   - Use HTTPS if possible (configure on Pi #1)
   - Rate limit API calls to prevent abuse

## Scalability and Limitations

### Current Design (Single Pi 5)
- ✅ Suitable for home/small office (< 20 devices)
- ✅ Can handle ~100 Mbps mirrored traffic
- ✅ Retains 7-14 days of logs

### Scaling Up
If traffic or device count grows:
1. **More Storage**: Add external SSD or NAS for Loki
2. **Distributed Loki**: Run Loki in microservices mode (out of scope for Pi)
3. **Rule Tuning**: Disable low-value Suricata rules to reduce load
4. **Sampling**: Process only a percentage of traffic or time windows

### Known Limitations
- AI Hat inference: ~13 TOPS (suitable for small models)
- Disk I/O: SD card or slow USB storage will bottleneck Loki writes
- No redundancy: Single point of failure (acceptable for home lab)

## Future Enhancements

1. **Zeek Integration**: Add Zeek for richer protocol analysis
2. **Threat Intel Feeds**: Integrate external IoC feeds (MISP, AlienVault)
3. **Alerting**: Add Grafana Alerting or Prometheus Alertmanager
4. **User Notifications**: Slack/email alerts for critical events
5. **Model Retraining**: Periodic retraining on local network data
6. **Honeypot Integration**: Add honeypot logs to Loki for additional intel

---

**See Also**:
- [pi2-setup.md](pi2-setup.md) for installation steps
- [logging-and-dashboards.md](logging-and-dashboards.md) for Grafana/Loki usage
- [ai-stack.md](ai-stack.md) for AI service details

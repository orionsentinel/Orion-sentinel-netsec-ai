# NetSec Pi Architecture

This document describes the production architecture for the **Orion Sentinel NetSec Pi** - a network security sensor stack designed for Raspberry Pi 5 with NVMe HAT.

## System Roles

The Orion Sentinel ecosystem consists of three logical nodes:

### 1. NetSec Pi (This Repository)

**Hardware:**
- Raspberry Pi 5 (4-8GB RAM recommended)
- NVMe HAT with M.2 NVMe SSD (minimum 128GB recommended)
- Optional: Dedicated network interface for SPAN/mirrored traffic
- No AI HAT required for base deployment

**Operating System:**
- Raspberry Pi OS Lite (64-bit) or Debian-based ARM64 OS
- Docker and Docker Compose installed

**Responsibilities:**
- Run Suricata IDS as a network sensor (inline or SPAN/tap mode)
- Capture and analyze network traffic from mirrored switch port
- Store logs and PCAPs on NVMe storage (not microSD)
- Ship logs and metrics to CoreSrv (Loki and Prometheus)
- Optionally expose local EveBox UI for NSM analysis
- Provide node health metrics via Node Exporter

**What It Does NOT Do:**
- Does not run Grafana (uses CoreSrv's Grafana)
- Does not run Prometheus (metrics scraped by CoreSrv)
- Does not run local Loki in production (SPoG mode)
- Does not require AI HAT (AI node is separate, optional)

### 2. CoreSrv Node (Separate Repository: Orion-Sentinel-CoreSrv)

**Hardware:**
- Separate server/workstation (Dell mini-PC, NUC, or similar)
- x86_64 or ARM64
- Sufficient storage for log retention

**Services:**
- **Loki** - Central log aggregation for all Orion nodes
- **Grafana** - Dashboards and visualization for all nodes
- **Prometheus** - Metrics collection from all nodes
- **Uptime Kuma** - Service monitoring and alerting
- **Dashy** - Service dashboard homepage
- **Traefik** - Reverse proxy with SSL/TLS
- **Authelia** - Authentication gateway (optional)

**Integration:**
- NetSec Pi sends logs to CoreSrv Loki via Promtail
- NetSec Pi exposes metrics for CoreSrv Prometheus scraping
- Grafana dashboards on CoreSrv visualize NetSec data
- Optional: NetSec Web UI proxied through CoreSrv Traefik

### 3. Future AI Node (Separate Pi 5 with AI HAT - Not Required for v1)

**Status:** Documented but not implemented in base deployment

**Hardware (Future):**
- Raspberry Pi 5 with AI HAT (Hailo-8L or similar)
- No NVMe required (uses SD card or USB storage)

**Responsibilities (Future):**
- Read logs from CoreSrv Loki via API
- Perform AI inference (anomaly detection, threat classification)
- Compute risk scores and enrichments
- Publish enriched alerts back to Loki or HTTP API
- Optional: Subscribe to event streams from CoreSrv

**Non-Goals:**
- Not required for base NSM operation
- If offline, NetSec stack continues working
- No hard dependencies from NetSec stack to AI node

See [docs/ai-node-future.md](./ai-node-future.md) for detailed AI node architecture.

---

## NetSec Pi Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Network Switch                              │
│                    (Port Mirroring Enabled)                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Mirrored Traffic (SPAN)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       NetSec Pi (Raspberry Pi 5)                     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     Network Interface (eth0)                   │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │ Raw packets                           │
│                              ▼                                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Suricata IDS (network_mode: host)                            │  │
│  │  • Passive packet capture via AF_PACKET                       │  │
│  │  • Signature-based detection (ET Open rules)                  │  │
│  │  • Protocol analysis (HTTP, TLS, DNS, etc.)                   │  │
│  │  • EVE JSON logging → /mnt/orion-nvme-netsec/suricata/logs    │  │
│  │  • Optional PCAP storage → /mnt/orion-nvme-netsec/suricata/pcaps│ │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │ eve.json                              │
│                              ▼                                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Promtail (Loki Agent)                                        │  │
│  │  • Tails Suricata eve.json                                    │  │
│  │  • Tails system logs (/var/log)                               │  │
│  │  • Applies labels:                                            │  │
│  │    - orion_node_role: netsec                                  │  │
│  │    - orion_node_name: netsec-pi-01                            │  │
│  │    - app: suricata                                            │  │
│  │  • Ships to CoreSrv Loki (HTTP push)                          │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │ HTTP/gRPC                             │
│                              ▼                                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Node Exporter (Prometheus Exporter)                          │  │
│  │  • System metrics: CPU, RAM, disk, network I/O                │  │
│  │  • Exposed on port 9100                                       │  │
│  │  • Scraped by CoreSrv Prometheus                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  EveBox (Optional - netsec-plus-evebox profile)               │  │
│  │  • Local web UI for Suricata alerts                           │  │
│  │  • Reads eve.json from NVMe                                   │  │
│  │  • Port 5636 (configurable)                                   │  │
│  │  • Used for local troubleshooting and analysis                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  NVMe Storage: /mnt/orion-nvme-netsec                         │  │
│  │  └── suricata/                                                │  │
│  │      ├── logs/        (eve.json, fast.log, stats.log)         │  │
│  │      ├── pcaps/       (optional full packet captures)         │  │
│  │      └── rules/       (Suricata rule files)                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ Logs & Metrics
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CoreSrv (Separate Node)                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Loki (receives logs from Promtail)                            │ │
│  │  Prometheus (scrapes Node Exporter on NetSec Pi)               │ │
│  │  Grafana (dashboards for NetSec monitoring)                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Steps:

1. **Packet Capture**
   - Network switch mirrors all traffic to NetSec Pi's interface
   - Suricata captures packets in passive mode (no inline blocking)

2. **Detection & Logging**
   - Suricata analyzes traffic with signature rules
   - Generates EVE JSON events for alerts, flows, DNS, HTTP, TLS
   - Writes logs to `/mnt/orion-nvme-netsec/suricata/logs/eve.json`
   - Optional: Stores PCAPs to `/mnt/orion-nvme-netsec/suricata/pcaps/`

3. **Log Shipping**
   - Promtail tails eve.json and system logs
   - Applies consistent labels for filtering
   - Ships logs to CoreSrv Loki via HTTP

4. **Metrics Export**
   - Node Exporter exposes system metrics on port 9100
   - CoreSrv Prometheus scrapes metrics periodically

5. **Visualization**
   - CoreSrv Grafana queries Loki for logs
   - CoreSrv Grafana queries Prometheus for metrics
   - Dashboards show alerts, top talkers, node health

---

## NVMe Storage Layout

### Why NVMe?

Raspberry Pi microSD cards have:
- Limited write endurance (wear out quickly)
- Slow write speeds (bottleneck for high-traffic networks)
- Risk of corruption on power loss

NVMe SSDs provide:
- High write endurance (millions of write cycles)
- Fast sequential and random I/O
- Better reliability for 24/7 operation

### Required Host Configuration

**1. Mount NVMe Drive**

Create mount point and format NVMe (one-time setup):

```bash
# Identify NVMe device (usually /dev/nvme0n1)
lsblk

# Create partition (if needed)
sudo fdisk /dev/nvme0n1
# Create new partition: n, p, 1, <enter>, <enter>, w

# Format as ext4
sudo mkfs.ext4 /dev/nvme0n1p1

# Create mount point
sudo mkdir -p /mnt/orion-nvme-netsec

# Mount
sudo mount /dev/nvme0n1p1 /mnt/orion-nvme-netsec
```

**2. Add to /etc/fstab for Persistent Mounting**

Get UUID:
```bash
sudo blkid /dev/nvme0n1p1
```

Add to `/etc/fstab`:
```
UUID=<your-uuid-here>  /mnt/orion-nvme-netsec  ext4  defaults,noatime  0  2
```

Verify:
```bash
sudo mount -a
df -h /mnt/orion-nvme-netsec
```

**3. Create Directory Structure**

```bash
sudo mkdir -p /mnt/orion-nvme-netsec/suricata/logs
sudo mkdir -p /mnt/orion-nvme-netsec/suricata/pcaps
sudo mkdir -p /mnt/orion-nvme-netsec/suricata/rules
sudo mkdir -p /mnt/orion-nvme-netsec/promtail

# Set ownership (Suricata runs as UID 1000 in container typically)
sudo chown -R 1000:1000 /mnt/orion-nvme-netsec/suricata
sudo chown -R 1000:1000 /mnt/orion-nvme-netsec/promtail
```

### Docker Volume Mounts

The compose file bind-mounts NVMe directories:

```yaml
volumes:
  # Suricata logs → NVMe
  - /mnt/orion-nvme-netsec/suricata/logs:/var/log/suricata
  
  # Suricata PCAPs → NVMe (optional, high disk usage)
  - /mnt/orion-nvme-netsec/suricata/pcaps:/var/log/suricata/pcap
  
  # Suricata rules → NVMe (persistent across updates)
  - /mnt/orion-nvme-netsec/suricata/rules:/var/lib/suricata
```

### Storage Estimates

| Component | Retention | Est. Size (1 Gbps network) |
|-----------|-----------|----------------------------|
| EVE JSON logs | 7 days | 10-50 GB |
| PCAPs (if enabled) | 24 hours | 100-500 GB |
| Suricata rules | N/A | 100 MB |

For typical home networks (100-500 Mbps), expect:
- **EVE JSON logs**: 2-10 GB per week
- **PCAPs** (if enabled): 20-100 GB per day

**Recommendation:** 256 GB NVMe minimum, 512 GB preferred if storing PCAPs.

---

## Docker Compose Profiles

The NetSec Pi stack uses Docker Compose profiles for flexible deployments.

### Profile: `netsec-minimal` (Production Default)

**Services:**
- Suricata IDS
- Promtail (Loki client)
- Node Exporter (metrics)

**Use case:** Production sensor feeding CoreSrv

**Start command:**
```bash
docker compose --profile netsec-minimal up -d
```

### Profile: `netsec-plus-evebox`

**Services:**
- All from `netsec-minimal`
- EveBox (local web UI for Suricata alerts)

**Use case:** NetSec Pi with local troubleshooting UI

**Start command:**
```bash
docker compose --profile netsec-plus-evebox up -d
```

**Access EveBox:** http://netsec-pi-ip:5636

### Profile: `netsec-debug`

**Services:**
- Toolbox container (Alpine with tcpdump, dig, curl, etc.)

**Use case:** Network troubleshooting and diagnostics

**Start command:**
```bash
docker compose --profile netsec-debug up -d
```

**Usage:**
```bash
docker exec -it orion-netsec-debug /bin/sh
# tcpdump -i eth0 -nn 'port 53'
# dig @8.8.8.8 google.com
# curl -v http://192.168.1.1
```

---

## Integration with CoreSrv

### Loki Integration

**NetSec Pi Configuration (.env):**
```bash
LOKI_URL=http://192.168.x.x:3100  # CoreSrv IP
```

**Promtail Labels (applied automatically):**
```yaml
orion_node_role: netsec
orion_node_name: netsec-pi-01  # from .env NODE_NAME
app: suricata
stream: eve-json
job: netsec
```

**Example Loki Queries (run on CoreSrv Grafana):**

Show all Suricata alerts from last 24h:
```logql
{orion_node_role="netsec", app="suricata"} 
  | json 
  | event_type="alert"
```

Show high-severity alerts:
```logql
{orion_node_role="netsec", app="suricata"} 
  | json 
  | event_type="alert" 
  | severity >= 1
```

Top source IPs generating alerts:
```logql
topk(10, 
  sum by (src_ip) (
    count_over_time({orion_node_role="netsec", app="suricata"} 
      | json 
      | event_type="alert" [24h]
    )
  )
)
```

### Prometheus Integration

**NetSec Pi Exposes:**
- Node Exporter on port 9100 (system metrics)
- Optional: Suricata metrics exporter (if configured)

**CoreSrv Prometheus Scrape Config:**

Add to CoreSrv's `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'netsec-pi-01'
    static_configs:
      - targets: ['192.168.x.x:9100']  # NetSec Pi IP
        labels:
          orion_node_role: 'netsec'
          orion_node_name: 'netsec-pi-01'
          instance: 'netsec-pi-01'
```

**Example Prometheus Queries:**

NetSec Pi CPU usage:
```promql
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle", orion_node_role="netsec"}[5m])) * 100)
```

NetSec Pi disk usage:
```promql
(node_filesystem_size_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"} 
 - node_filesystem_free_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"}) 
/ node_filesystem_size_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"} * 100
```

Suricata events per second (if metrics enabled):
```promql
rate(suricata_events_total{orion_node_role="netsec"}[5m])
```

### Grafana Dashboards

See [docs/grafana-dashboards.md](./grafana-dashboards.md) for:
- NetSec Pi health dashboard
- Suricata alerts dashboard
- Top talkers and destinations
- DNS query analysis

---

## Security Considerations

### Container Security

**Suricata:**
- Runs in `network_mode: host` (required for packet capture)
- Capabilities: NET_ADMIN, NET_RAW, SYS_NICE (required for AF_PACKET)
- All other capabilities dropped
- Read-only config volume
- Logs written to NVMe volume only

**Promtail:**
- No special capabilities required
- Read-only access to log directories
- Network access to Loki only

**Node Exporter:**
- Read-only access to /proc and /sys
- No write access needed

**EveBox (optional):**
- Read-only access to eve.json
- Exposes port 5636 (bind to LAN interface only, not 0.0.0.0)

### Host Security Recommendations

**Firewall (ufw):**
```bash
# Default deny incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (from trusted network only)
sudo ufw allow from 192.168.x.0/24 to any port 22

# Allow Node Exporter (from CoreSrv only)
sudo ufw allow from 192.168.x.x to any port 9100 proto tcp

# Allow EveBox (from LAN only, if using)
sudo ufw allow from 192.168.x.0/24 to any port 5636 proto tcp

# Enable firewall
sudo ufw enable
```

**SSH Hardening:**
- Disable password authentication (use SSH keys only)
- Change default SSH port (optional)
- Use fail2ban for brute-force protection

**Updates:**
- Enable unattended-upgrades for security patches
- Regularly update Docker images
- Monitor CVE feeds for Suricata and other components

**Network Isolation:**
- NetSec Pi should NOT be exposed to the internet
- Use VPN (WireGuard, Tailscale) for remote access
- Place on dedicated management VLAN (optional)

### Data Privacy

All data processing happens locally:
- No cloud dependencies
- No telemetry or phone-home
- Logs stay on NVMe or CoreSrv (both on-premises)

---

## Monitoring and Maintenance

### Health Checks

Use the provided script:
```bash
./scripts/check-nvme.sh
```

Checks:
- NVMe mount exists
- Sufficient free space (warns at 80%, fails at 95%)
- Write permissions

Run before starting services or in cron for monitoring.

### Log Rotation

Suricata logs are managed by:
1. **Suricata internal rotation** (configured in suricata.yaml)
2. **Promtail** (tails rotated files automatically)
3. **Loki retention** (configured on CoreSrv, typically 7-30 days)

PCAPs (if enabled) should be rotated manually or via cron:
```bash
# Delete PCAPs older than 24 hours
find /mnt/orion-nvme-netsec/suricata/pcaps -name "*.pcap" -mtime +1 -delete
```

### Backup Recommendations

**What to backup:**
- `.env` file (configuration)
- `config/` directory (custom configs)
- Suricata custom rules (if any)

**What NOT to backup:**
- Logs (ephemeral, retained in Loki)
- PCAPs (too large, ephemeral)
- Docker volumes (recreated automatically)

---

## Smoke Tests

Run these tests to validate your NetSec Pi deployment.

### 1. Pre-flight Host Check

**Verify NVMe storage is ready:**

```bash
# Run the NVMe health check script
./scripts/check-nvme.sh

# Expected output:
# [INFO] NVMe mount point exists: /mnt/orion-nvme-netsec
# [INFO] NVMe is mounted at /mnt/orion-nvme-netsec
# [INFO] Disk usage: X% used, Y GB free
# [INFO] All checks PASSED ✓
```

**Environment variables for check-nvme.sh:**
- `NVME_MOUNT=/mnt/orion-nvme-netsec` - NVMe mount path
- `MIN_FREE_GB=5` - Minimum free space in GB

### 2. Container Startup

**Start minimal stack and verify no crash-loops:**

```bash
# Start services
docker compose --profile netsec-minimal up -d

# Wait 30 seconds for services to initialize
sleep 30

# Check all services are running (not restarting)
docker compose ps

# Expected: All services show "running" status
# - orion-netsec-suricata
# - orion-netsec-promtail
# - orion-netsec-node-exporter
```

### 3. Suricata EVE Output

**Confirm Suricata is capturing and logging:**

```bash
# Check Suricata container logs for packet capture
docker logs orion-netsec-suricata 2>&1 | grep -i "received"

# Check if eve.json exists on NVMe
ls -la /mnt/orion-nvme-netsec/suricata/logs/eve.json

# View recent events
docker exec orion-netsec-suricata tail -5 /var/log/suricata/eve.json

# Generate a test alert (from another device or the Pi)
curl https://testmyids.com

# Verify the test alert appears
docker exec orion-netsec-suricata tail /var/log/suricata/eve.json | jq 'select(.event_type=="alert")'
```

### 4. Promtail → Loki

**Verify logs are being shipped to CoreSrv Loki:**

```bash
# Check Promtail logs for successful shipping
docker logs orion-netsec-promtail 2>&1 | grep -i "POST"
# Expected: "POST /loki/api/v1/push (200 OK)"

# Verify Loki connectivity (replace with your CoreSrv IP)
docker exec orion-netsec-promtail wget -q -O- http://192.168.x.x:3100/ready
# Expected: "ready"
```

**Example Loki query (run on CoreSrv Grafana):**

```logql
{orion_node_role="netsec", app="suricata"} | json | event_type="alert"
```

### 5. Node Exporter

**Verify CoreSrv can scrape metrics:**

```bash
# Test Node Exporter endpoint locally
curl -s http://localhost:9100/metrics | head -20

# Test from CoreSrv (replace with NetSec Pi IP)
curl -s http://192.168.x.x:9100/metrics | head -20

# Expected: Prometheus metrics output
```

**Validate in CoreSrv Prometheus:**

1. Open Prometheus UI: `http://coresrv:9090`
2. Go to Status → Targets
3. Find `netsec-node-exporter` job
4. Verify state is "UP"

### 6. EveBox (if enabled)

**Verify local alert UI is accessible:**

```bash
# Start with EveBox profile
docker compose --profile netsec-plus-evebox up -d

# Test EveBox HTTP endpoint
curl -s http://localhost:5636/ | head -5

# Or open in browser
# http://netsec-pi-ip:5636
```

**Verify EveBox sees Suricata events:**

1. Open EveBox in browser
2. Check Events tab
3. Should see recent alerts and flows

### Quick Validation Script

Run this all-in-one validation:

```bash
make test
```

This runs:
1. NVMe storage check
2. Service status check
3. Suricata capture verification
4. Promtail shipping verification
5. Node Exporter endpoint test

---

## Troubleshooting

### Suricata not capturing traffic

**Check interface:**
```bash
docker exec orion-suricata suricata --build-info | grep AF_PACKET
docker logs orion-suricata | grep "Using AF_PACKET"
```

**Verify SPAN port:**
```bash
# On host
sudo tcpdump -i eth0 -c 10
# Should see mirrored traffic
```

**Check stats:**
```bash
docker exec orion-suricata tail /var/log/suricata/stats.log
# Look for capture.kernel_packets > 0
```

### Promtail not shipping logs

**Check Loki connectivity:**
```bash
docker exec orion-promtail wget -O- http://192.168.x.x:3100/ready
# Should return "ready"
```

**Check Promtail logs:**
```bash
docker logs orion-promtail | grep -i error
docker logs orion-promtail | grep "POST /loki/api/v1/push"
# Should see successful 200 OK responses
```

### NVMe out of space

**Check usage:**
```bash
df -h /mnt/orion-nvme-netsec
du -sh /mnt/orion-nvme-netsec/suricata/logs
du -sh /mnt/orion-nvme-netsec/suricata/pcaps
```

**Clean up:**
```bash
# Disable PCAP logging in suricata.yaml if not needed
# Reduce Loki retention on CoreSrv
# Manually delete old PCAPs
```

### High CPU usage

**Check Suricata stats:**
```bash
docker exec orion-suricata suricatasc -c stats | jq .
```

**Tune Suricata:**
- Reduce rule sets (disable unused categories)
- Adjust AF_PACKET ring-size
- Increase worker threads (if multi-core Pi)

See Suricata docs: https://suricata.readthedocs.io/en/latest/performance/tuning.html

---

## Next Steps

1. Set up CoreSrv node (see Orion-Sentinel-CoreSrv repo)
2. Configure network switch for port mirroring
3. Install and mount NVMe on NetSec Pi
4. Deploy NetSec stack with `netsec-minimal` profile
5. Import Grafana dashboards on CoreSrv
6. (Future) Add AI node for enhanced detection

For quickstart guide, see main [README.md](../README.md).

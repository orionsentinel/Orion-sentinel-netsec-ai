# Pi #2 Setup Guide

This guide walks through setting up Pi #2 (Security Pi) to run the Orion Sentinel NSM + AI stack.

## Prerequisites

### Hardware Requirements
- **Raspberry Pi 5** (8 GB RAM recommended, 4 GB minimum)
- **Raspberry Pi AI Hat** (optional but recommended for AI inference)
- **MicroSD card** (32 GB+, UHS-I/U3 or better) OR **NVMe SSD via HAT+**
- **Power supply** (27W USB-C PD or official Pi 5 power supply)
- **Ethernet cable** (Gigabit recommended)
- **Case with cooling** (active cooling recommended for sustained workloads)

### Network Requirements
- **Managed switch or router with port mirroring** (SPAN/TAP capability)
- **Dedicated network interface** for mirrored traffic (can be the same as management interface for testing)
- **Static IP or DHCP reservation** for Pi #2
- **Network access to Pi #1** (for DNS log shipping and Pi-hole API calls)

### Software Prerequisites
- Raspberry Pi OS (64-bit) - Debian Bookworm or later
- Docker Engine (24.0+)
- Docker Compose (2.20+)

---

## Step 1: Install Raspberry Pi OS

### 1.1 Download and Flash OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

1. **OS**: Raspberry Pi OS (64-bit) - Lite or Desktop
2. **Storage**: Select your microSD card or SSD
3. **Settings** (gear icon):
   - Set hostname: `pi2-security` (or your preference)
   - Enable SSH with password or public key
   - Configure WiFi (if needed, though Ethernet is recommended)
   - Set locale and keyboard

4. Write and boot the Pi

### 1.2 First Boot and Update

```bash
# SSH into the Pi
ssh pi@pi2-security.local  # Or use IP address

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y git vim curl htop net-tools tcpdump
```

### 1.3 Configure Static IP (Optional but Recommended)

Edit `/etc/dhcpcd.conf`:
```bash
sudo nano /etc/dhcpcd.conf
```

Add (adjust for your network):
```bash
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.10  # Pi #1's VIP or primary DNS
```

Reboot:
```bash
sudo reboot
```

---

## Step 2: Install Docker and Docker Compose

### 2.1 Install Docker

```bash
# Install Docker using convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify Docker installation
docker --version
docker run hello-world
```

### 2.2 Install Docker Compose

Docker Compose v2 is included with Docker Engine 24.0+. Verify:

```bash
docker compose version
```

If not installed:
```bash
sudo apt install -y docker-compose-plugin
```

---

## Step 3: Optimize Pi for Network Monitoring

### 3.1 Increase File Descriptor Limits

Suricata and Loki need more file descriptors:

```bash
sudo nano /etc/security/limits.conf
```

Add:
```
* soft nofile 65536
* hard nofile 65536
```

### 3.2 Disable Swap (Optional for SSD)

If using an SSD, you may disable swap to reduce wear:

```bash
sudo dphys-swapfile swapoff
sudo dphys-swapfile uninstall
sudo systemctl disable dphys-swapfile
```

### 3.3 Enable Performance Governor (Optional)

For sustained performance:

```bash
echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

To make permanent, add to `/etc/rc.local`:
```bash
sudo nano /etc/rc.local
```

Before `exit 0`, add:
```bash
echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu2/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu3/cpufreq/scaling_governor
```

---

## Step 4: Configure Network Interface for Port Mirroring

### 4.1 Identify Network Interface

```bash
ip link show
```

You should see interfaces like:
- `eth0`: Primary Ethernet (for management and mirrored traffic)
- `eth1`: Secondary Ethernet (if you have USB Ethernet adapter)
- `wlan0`: WiFi

**Recommendation**: Use a dedicated interface for mirrored traffic if possible. Otherwise, `eth0` can be used for both management and monitoring.

### 4.2 Disable IP on Mirrored Interface (if using dedicated interface)

If using a dedicated interface (e.g., `eth1`) for mirrored traffic only:

```bash
sudo nano /etc/dhcpcd.conf
```

Add:
```bash
denyinterfaces eth1
```

Bring interface up in promiscuous mode:
```bash
sudo ip link set eth1 up promisc on
```

Add to `/etc/rc.local` to persist:
```bash
ip link set eth1 up promisc on
```

### 4.3 Configure Port Mirroring on Switch/Router

This is device-specific. Example for common managed switches:

**TP-Link T1600G**:
1. Web UI → Monitoring → Port Mirroring
2. Source Port: Select all LAN ports
3. Destination Port: Port connected to Pi #2's `eth1`
4. Direction: Both
5. Apply

**GL.iNet Router**:
- Not all models support port mirroring. Check documentation.
- Alternatively, use the router as a transparent bridge or configure iptables to TEE packets.

**Verification**:
```bash
# On Pi #2, verify traffic is being mirrored
sudo tcpdump -i eth1 -c 100
# You should see traffic from other devices on your LAN
```

---

## Step 5: Clone Repository and Configure

### 5.1 Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/orion-sentinel-nsm-ai.git
cd orion-sentinel-nsm-ai
```

### 5.2 Create Environment Files

**NSM Stack**:
```bash
cd stacks/nsm
cp .env.example .env
nano .env
```

Edit `.env`:
```bash
# Network interface for Suricata (mirrored traffic)
NSM_IFACE=eth0  # Change to eth1 if using dedicated interface

# Loki retention (days)
LOKI_RETENTION_DAYS=7

# Grafana admin password (CHANGE THIS!)
GRAFANA_ADMIN_PASSWORD=your-secure-password
```

**AI Stack**:
```bash
cd ../ai
cp .env.example .env
nano .env
```

Edit `.env`:
```bash
# Loki URL (internal Docker network)
LOKI_URL=http://loki:3100

# Pi-hole API (on Pi #1)
PIHOLE_API_URL=http://192.168.1.10/admin/api.php  # Change to Pi #1's IP
PIHOLE_API_TOKEN=your-pihole-api-token

# Model paths
DEVICE_ANOMALY_MODEL=/models/device_anomaly.onnx
DOMAIN_RISK_MODEL=/models/domain_risk.onnx

# Detection thresholds
DEVICE_ANOMALY_THRESHOLD=0.7
DOMAIN_RISK_THRESHOLD=0.85

# Batch processing interval (minutes)
BATCH_INTERVAL=10
```

---

## Step 6: Deploy NSM Stack

### 6.1 Start NSM Services

```bash
cd ~/orion-sentinel-nsm-ai/stacks/nsm
docker compose up -d
```

### 6.2 Verify Services

```bash
# Check running containers
docker compose ps

# Check Suricata logs
docker compose logs suricata

# Check Loki health
curl http://localhost:3100/ready

# Check Grafana
# Open browser: http://pi2-ip:3000
# Login: admin / <password-from-env>
```

### 6.3 Verify Suricata is Capturing Traffic

```bash
# Check Suricata stats
docker compose exec suricata suricatasc -c "capture-stats"

# Tail eve.json to see events
docker compose exec suricata tail -f /var/log/suricata/eve.json
```

You should see JSON events for DNS, flows, etc.

### 6.4 Update Suricata Rules

```bash
# Update ET Open ruleset
docker compose exec suricata suricata-update

# Restart Suricata to apply new rules
docker compose restart suricata
```

---

## Step 7: Deploy AI Stack

### 7.1 Prepare AI Models

**NOTE**: You need to provide your own ONNX or TFLite models. Place them in:

```bash
mkdir -p ~/orion-sentinel-nsm-ai/stacks/ai/models
```

Copy your models:
```bash
# Example (you'll need to download or train these)
cp /path/to/device_anomaly.onnx ~/orion-sentinel-nsm-ai/stacks/ai/models/
cp /path/to/domain_risk.onnx ~/orion-sentinel-nsm-ai/stacks/ai/models/
```

**Placeholder Models**:
If you don't have models yet, the AI service will log warnings but continue to run. You can develop and test feature extraction without models.

### 7.2 Start AI Service

```bash
cd ~/orion-sentinel-nsm-ai/stacks/ai
docker compose up -d
```

### 7.3 Verify AI Service

```bash
# Check logs
docker compose logs orion-ai

# Check health endpoint (if HTTP server is enabled)
curl http://localhost:8080/health
```

---

## Step 8: Configure DNS Log Shipping from Pi #1

**This step is performed on Pi #1** (in the `orion-sentinel-dns-ha` repo).

See [integration-orion-dns-ha.md](integration-orion-dns-ha.md) for detailed instructions.

**Summary**:
1. Install Promtail on Pi #1
2. Configure Promtail to ship Pi-hole and Unbound logs
3. Point Promtail to Pi #2's Loki endpoint: `http://<pi2-ip>:3100/loki/api/v1/push`
4. Ensure Pi #2's firewall allows port 3100 from Pi #1

**Verification** (on Pi #2):
```bash
# Query Loki for DNS logs
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="pihole"}' | jq
```

---

## Step 9: Access Grafana and Create Dashboards

### 9.1 Login to Grafana

1. Open browser: `http://pi2-ip:3000`
2. Login: `admin` / `<password-from-env>`
3. **Important**: Change the admin password immediately!

### 9.2 Verify Loki Datasource

1. Left menu → Configuration → Data sources
2. You should see "Loki" already configured (from datasources.yml)
3. Click "Test" to verify connection

### 9.3 Explore Logs

1. Left menu → Explore
2. Select "Loki" datasource
3. Try queries:
   - `{service="suricata"}` - All Suricata events
   - `{service="pihole"}` - Pi-hole DNS queries (if Pi #1 is shipping)
   - `{service="ai"}` - AI detection results
   - `{service="suricata"} |= "alert"` - Only Suricata alerts

### 9.4 Import Dashboards

(Dashboards can be created manually or imported from JSON files - to be added later)

See [logging-and-dashboards.md](logging-and-dashboards.md) for example queries and dashboard configurations.

---

## Step 10: Monitoring and Maintenance

### 10.1 Check Resource Usage

```bash
# Overall system
htop

# Docker container stats
docker stats

# Disk usage
df -h
```

### 10.2 Log Rotation

Loki will automatically compact and delete old logs based on `LOKI_RETENTION_DAYS`.

For Suricata eve.json, configure logrotate:

```bash
sudo nano /etc/logrotate.d/suricata
```

```
/var/log/suricata/eve.json {
    daily
    rotate 3
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
    postrotate
        docker compose -f /home/pi/orion-sentinel-nsm-ai/stacks/nsm/docker-compose.yml restart suricata
    endscript
}
```

### 10.3 Update Services

```bash
# Pull latest images
cd ~/orion-sentinel-nsm-ai/stacks/nsm
docker compose pull
docker compose up -d

cd ~/orion-sentinel-nsm-ai/stacks/ai
docker compose pull
docker compose up -d
```

### 10.4 Backup Configuration

Regularly backup:
- `.env` files (without sensitive tokens - store those securely separately)
- Grafana dashboards (export as JSON)
- AI models
- Loki data (optional - can be regenerated)

---

## Troubleshooting

### Suricata Not Capturing Traffic

**Check**:
1. Interface is correct in `.env`
2. Interface is up and in promiscuous mode: `ip link show eth1`
3. Port mirroring is configured correctly on switch
4. Run `tcpdump -i eth1` to verify raw packets are visible

**Fix**:
```bash
sudo ip link set eth1 up promisc on
docker compose restart suricata
```

### Loki Out of Disk Space

**Check**:
```bash
df -h
du -sh ~/orion-sentinel-nsm-ai/stacks/nsm/loki/data
```

**Fix**:
1. Reduce `LOKI_RETENTION_DAYS` in `.env`
2. Manually delete old chunks: `rm -rf ~/orion-sentinel-nsm-ai/stacks/nsm/loki/data/loki/chunks/<old-dir>`
3. Restart Loki: `docker compose restart loki`

### Grafana Can't Connect to Loki

**Check**:
```bash
# From Grafana container
docker compose exec grafana curl http://loki:3100/ready

# From host
curl http://localhost:3100/ready
```

**Fix**:
- Ensure Loki is running: `docker compose ps loki`
- Check Loki logs: `docker compose logs loki`

### AI Service Not Reading Logs

**Check**:
- Loki URL is correct in AI service `.env`
- Loki is reachable from AI container: `docker compose exec orion-ai curl http://loki:3100/ready`
- Logs exist in Loki: Query via Grafana or API

**Fix**:
- Verify `LOKI_URL` in `.env`
- Restart AI service: `docker compose restart orion-ai`

### DNS Logs Not Appearing from Pi #1

**Check** (on Pi #1):
- Promtail is running
- Promtail config has correct Loki URL
- Network connectivity: `curl http://<pi2-ip>:3100/ready`
- Firewall on Pi #2 allows port 3100 from Pi #1

**Fix** (on Pi #2):
```bash
sudo ufw allow from <pi1-ip> to any port 3100
```

---

## Next Steps

1. **Create Grafana Dashboards**: See [logging-and-dashboards.md](logging-and-dashboards.md)
2. **Train AI Models**: See [ai-stack.md](ai-stack.md) for model development
3. **Fine-tune Suricata Rules**: Disable noisy rules, enable relevant ones
4. **Set up Alerting**: Configure Grafana Alerting for critical events

---

**See Also**:
- [architecture.md](architecture.md) for system design details
- [logging-and-dashboards.md](logging-and-dashboards.md) for Grafana usage
- [ai-stack.md](ai-stack.md) for AI service configuration

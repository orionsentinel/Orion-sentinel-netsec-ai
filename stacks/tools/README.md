# Orion Sentinel - NetSec Tools

Network security analysis and data manipulation tools for the NetSec Pi.

## 🛠️ Tools Included

### 1. CyberChef
**Purpose:** Data transformation and analysis  
**Access:** http://netsec-pi-ip:8000  
**Use Cases:**
- Decode/encode data (Base64, hex, etc.)
- Parse and analyze network payloads
- Convert between data formats
- Decrypt/encrypt test data
- Extract IOCs from logs

### 2. ntopng
**Purpose:** Real-time network traffic analysis  
**Access:** http://netsec-pi-ip:3000  
**Features:**
- Real-time traffic statistics and flows
- Top talkers and protocols
- Historical traffic analysis
- Network security insights
- Layer 7 protocol detection

## 🚀 Quick Start

### Enable Tools Profile

Edit the compose file to start the tools:
```bash
sudo nano <path-to-orion-sentinel-netsec>/compose.yml
```

Start services with the tools profile:
```bash
# Core NSM + NetSec Tools
docker compose --profile netsec-minimal --profile netsec-tools up -d

# Or with EveBox as well
docker compose --profile netsec-plus-evebox --profile netsec-tools up -d
```

Stop tools profile:
```bash
docker compose --profile netsec-tools down
```

### First-Time Setup

1. **Verify mirror port is working:**
   ```bash
   # Should see mirrored traffic from your switch
   sudo tcpdump -i eth1 -c 100
   ```

2. **Enable promiscuous mode (required for ntopng):**
   ```bash
   # Install systemd unit (one-time)
   sudo cp host/systemd/orion-netsec-promisc.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable orion-netsec-promisc.service
   sudo systemctl start orion-netsec-promisc.service

   # Verify
   ip link show eth1 | grep PROMISC
   ```

3. **Access the tools:**
   - CyberChef: http://192.168.x.x:8000 (replace with your Pi IP)
   - ntopng: http://192.168.x.x:3000

## 📊 ntopng Configuration

### Local Networks
Edit the local network CIDRs in the config:
```bash
sudo nano <path-to-orion-sentinel-netsec>/stacks/tools/ntopng/ntopng.conf
```

Change this line to match your network:
```conf
--local-networks "192.168.0.0/16"
```

Examples:
- Home network: `"192.168.0.0/16,10.0.0.0/8"`
- Corporate: `"10.0.0.0/8,172.16.0.0/12"`
- Multiple subnets: `"192.168.1.0/24,192.168.2.0/24"`

Restart after changes:
```bash
docker compose --profile netsec-tools restart ntopng
```

### Interface Configuration
By default, ntopng monitors `eth1` (matching NETSEC_INTERFACE default). If your mirror port is on a different interface:

**IMPORTANT:** You must update the interface in THREE places:

1. **Main .env file:**
   ```bash
   sudo nano <path-to-orion-sentinel-netsec>/.env
   ```
   
   Update:
   ```bash
   NETSEC_INTERFACE=eth0  # or your mirror interface
   ```

2. **ntopng.conf:**
   ```bash
   sudo nano <path-to-orion-sentinel-netsec>/stacks/tools/ntopng/ntopng.conf
   ```
   
   Change:
   ```conf
   --interface=eth0  # must match NETSEC_INTERFACE
   ```

3. **Systemd units (if using):**
   ```bash
   sudo nano /etc/systemd/system/orion-netsec-promisc.service
   sudo nano /etc/systemd/system/orion-netsec-nic-tuning.service
   ```
   
   Change `eth1` to your interface in both files.

4. **Restart everything:**
   ```bash
   # Restart Docker services
   docker compose down
   docker compose --profile netsec-minimal --profile netsec-tools up -d
   
   # Restart systemd services (if using)
   sudo systemctl restart orion-netsec-promisc.service
   sudo systemctl restart orion-netsec-nic-tuning.service
   ```

**Why multiple places?**
- Suricata uses NETSEC_INTERFACE from .env
- ntopng reads its config from ntopng.conf (doesn't support env vars)
- Systemd units run at host level (before Docker starts)
- All must monitor the SAME interface for consistency

## 🔐 Security Considerations

### ⚠️ LAN-Only Access
**CRITICAL:** These tools are designed for **LAN-only** access:
- Bound to 0.0.0.0 for LAN accessibility
- NO authentication by default (ntopng runs with `--disable-login`)
- **DO NOT** expose these ports via router/firewall to the internet

### Alternative: SSH Tunnel Access
For additional security, bind to localhost and access via SSH tunnel:

1. **Modify compose.yml** to bind to 127.0.0.1:
   ```yaml
   ports:
     - "127.0.0.1:8000:8000"  # CyberChef
     - "127.0.0.1:3000:3000"  # ntopng
   ```

2. **Access via SSH tunnel:**
   ```bash
   # From your workstation
   ssh -L 8000:localhost:8000 -L 3000:localhost:3000 pi@netsec-pi-ip
   
   # Then browse to:
   # http://localhost:8000 (CyberChef)
   # http://localhost:3000 (ntopng)
   ```

### Enabling Authentication (Production)
For production deployments, enable ntopng authentication:

1. Edit `ntopng.conf` and remove:
   ```conf
   # --disable-login=1  # Comment out or remove this line
   ```

2. Restart ntopng:
   ```bash
   docker compose --profile netsec-tools restart ntopng
   ```

3. Default credentials (first login):
   - Username: `admin`
   - Password: `admin`
   
4. **Change the password immediately** after first login!

## 📈 Monitoring and Validation

### Validate Mirror Port Traffic
```bash
# Basic packet capture test
sudo tcpdump -i eth1 -c 100 -nn

# Look for traffic from multiple sources (confirms mirroring)
sudo tcpdump -i eth1 -nn 'not host YOUR_PI_IP' | head -50

# Check for dropped packets (kernel)
sudo tcpdump -i eth1 -nn -vvv 2>&1 | grep dropped
```

### Monitor ntopng Packet Drops
Check ntopng web interface:
1. Navigate to http://netsec-pi-ip:3000
2. Go to **Settings → Interfaces → eth1**
3. Look for "Packet Drops" metric
4. If drops > 0, see "Performance Tuning" section below

### Monitor Suricata Drops
Suricata also captures on the mirror port and may report drops:
```bash
# Check Suricata stats log
tail -f /mnt/orion-nvme-netsec/suricata/logs/stats.log

# Look for lines containing:
# capture.kernel_drops
# decoder.pkts_dropped
```

## ⚡ Performance Tuning (Optional)

### Reduce Packet Drops
If you see packet drops in ntopng or Suricata:

1. **Disable NIC offloads** (optional systemd unit):
   ```bash
   sudo cp host/systemd/orion-netsec-nic-tuning.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable orion-netsec-nic-tuning.service
   sudo systemctl start orion-netsec-nic-tuning.service
   ```

2. **Verify offloads are disabled:**
   ```bash
   sudo ethtool -k eth1 | grep -E 'rx-checksumming|tx-checksumming|scatter-gather|tcp-segmentation-offload|generic-receive-offload'
   ```

3. **Increase ring buffer size:**
   ```bash
   # Check current size
   sudo ethtool -g eth1

   # Increase to maximum (if supported)
   sudo ethtool -G eth1 rx 4096 tx 4096
   ```

### Reduce ntopng CPU Usage
If ntopng uses too much CPU:

1. Edit `ntopng.conf`:
   ```bash
   sudo nano <path-to-orion-sentinel-netsec>/stacks/tools/ntopng/ntopng.conf
   ```

2. Add these lines:
   ```conf
   --disable-alerts
   --disable-host-persistency
   --max-num-hosts=1000  # Limit tracked hosts
   --max-num-flows=10000  # Limit tracked flows
   ```

3. Restart:
   ```bash
   docker compose --profile netsec-tools restart ntopng
   ```

## 🗂️ Data Storage

### CyberChef
- **Storage:** None (stateless tool, runs entirely in browser)
- **Backups:** Not required

### ntopng
- **Storage:** NVMe bind mount (not a Docker volume)
- **Location:** `${NVME_MOUNT}/ntopng` (default: `/mnt/orion-nvme-netsec/ntopng`)
- **Data:** Historical traffic statistics, flow data, host data
- **Retention:** Configurable in ntopng web UI (default: auto-purge old data)
- **Check space:** `df -h /mnt/orion-nvme-netsec`
- **Backup:** Include in NVMe backup strategy (if backing up NVMe data)

### Redis (ntopng dependency)
- **Storage:** Docker volume `redis-data` (ephemeral, can be lost)
- **Purpose:** Temporary cache for ntopng operations
- **Backups:** Not required (data is transient)

## 🔧 Troubleshooting

### CyberChef Not Loading
**Problem:** CyberChef page doesn't load

**Solutions:**
1. Check container is running:
   ```bash
   docker ps | grep cyberchef
   ```

2. Check logs:
   ```bash
   docker logs orion-netsec-cyberchef
   ```

3. Verify port binding:
   ```bash
   sudo netstat -tlnp | grep 8000
   ```

### ntopng Not Showing Traffic
**Problem:** ntopng shows no traffic or hosts

**Solutions:**
1. Verify promiscuous mode:
   ```bash
   ip link show eth1 | grep PROMISC
   ```

   If not present:
   ```bash
   sudo ip link set eth1 promisc on
   ```

2. Check interface has traffic:
   ```bash
   sudo tcpdump -i eth1 -c 10
   ```

   If no traffic, verify switch mirror port configuration.

3. Check ntopng logs:
   ```bash
   docker logs orion-netsec-ntopng
   ```

4. Verify Redis is running:
   ```bash
   docker ps | grep redis
   docker logs orion-netsec-redis
   ```

### High CPU Usage (Raspberry Pi 5)
**Problem:** Pi 5 runs hot or CPU usage is consistently high

**Solutions:**
1. Reduce ntopng tracking limits (see Performance Tuning)
2. Disable unnecessary ntopng features
3. Ensure active cooling (fan or heatsink)
4. Monitor CPU temperature:
   ```bash
   vcgencmd measure_temp
   ```
5. Consider reducing monitored protocols in ntopng settings

### Port Already in Use
**Problem:** Port 8000 or 3000 already in use

**Solutions:**
1. Check what's using the port:
   ```bash
   sudo netstat -tlnp | grep 8000
   sudo netstat -tlnp | grep 3000
   ```

2. Change port in `.env`:
   ```bash
   CYBERCHEF_PORT=8080  # Change from 8000
   NTOPNG_PORT=3030     # Change from 3000
   ```

3. Restart services:
   ```bash
   docker compose --profile netsec-tools down
   docker compose --profile netsec-minimal --profile netsec-tools up -d
   ```

## 🧹 Cleanup and Removal

### Remove Tools (keep data)
```bash
docker compose --profile netsec-tools down
```

### Remove Tools and Data
```bash
docker compose --profile netsec-tools down -v
```

### Remove Systemd Units
```bash
sudo systemctl stop orion-netsec-promisc.service
sudo systemctl disable orion-netsec-promisc.service
sudo rm /etc/systemd/system/orion-netsec-promisc.service

sudo systemctl stop orion-netsec-nic-tuning.service
sudo systemctl disable orion-netsec-nic-tuning.service
sudo rm /etc/systemd/system/orion-netsec-nic-tuning.service

sudo systemctl daemon-reload
```

## 📚 Additional Resources

- **CyberChef Documentation:** https://github.com/gchq/CyberChef/wiki
- **ntopng Documentation:** https://www.ntop.org/guides/ntopng/
- **ntopng Community Edition:** https://github.com/ntop/ntopng

## 🤝 Integration with Orion Sentinel

These tools complement the existing Orion Sentinel stack:

- **Suricata:** IDS/IPS detection (alerts on threats)
- **ntopng:** Traffic visibility (who talks to whom, protocols, bandwidth)
- **CyberChef:** Payload analysis (decode/transform suspicious data)
- **EveBox:** Alert triage (Suricata alert browser)
- **Grafana (CoreSrv):** Dashboards and alerting

**Typical workflow:**
1. Suricata detects suspicious traffic → alert in Grafana
2. Investigate in ntopng → identify hosts and flows
3. Extract payload from Suricata eve.json → decode in CyberChef
4. Correlate with other Orion logs in Loki/Grafana

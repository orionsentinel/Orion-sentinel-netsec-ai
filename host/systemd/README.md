# Orion Sentinel NetSec - Host Systemd Units

This directory contains optional systemd service units for host-level configuration required by the NetSec tools.

## Units Available

### 1. orion-netsec-promisc.service
**Purpose:** Enable promiscuous mode on the mirror/SPAN interface  
**Required for:** ntopng packet capture  
**Description:** Sets the network interface to promiscuous mode, allowing it to capture all packets on the mirror port, not just packets destined for the Pi.

**Installation:**
```bash
sudo cp orion-netsec-promisc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orion-netsec-promisc.service
sudo systemctl start orion-netsec-promisc.service
```

**Verification:**
```bash
# Check service status
sudo systemctl status orion-netsec-promisc.service

# Verify promiscuous mode is enabled
ip link show eth1 | grep PROMISC
```

**Customization:**
If your mirror port is NOT eth1, edit the service file:
```bash
sudo nano /etc/systemd/system/orion-netsec-promisc.service
```

Change `eth1` to your interface (e.g., `eth0`, `enx00e04c68xxxx`).

**IMPORTANT:** If you change the interface, you must also update:
- Main .env: NETSEC_INTERFACE
- stacks/tools/ntopng/ntopng.conf: --interface line
- host/systemd/orion-netsec-nic-tuning.service: interface name

### 2. orion-netsec-nic-tuning.service (Optional)
**Purpose:** Disable NIC offload features to reduce packet drops  
**Required for:** High-traffic environments with packet drops  
**Description:** Disables hardware offload features (GRO, LRO, GSO, TSO) that can cause packets to be coalesced or dropped before capture software sees them.

**When to use:**
- You see packet drops in ntopng statistics
- You see kernel drops in Suricata stats.log
- You have very high traffic volume on the mirror port (>100 Mbps sustained)

**When NOT to use:**
- Default setup works fine without drops
- You want to minimize CPU usage
- Your traffic volume is low to moderate

**Installation:**
```bash
sudo cp orion-netsec-nic-tuning.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orion-netsec-nic-tuning.service
sudo systemctl start orion-netsec-nic-tuning.service
```

**Verification:**
```bash
# Check service status
sudo systemctl status orion-netsec-nic-tuning.service

# Verify offloads are disabled
sudo ethtool -k eth1 | grep -E 'generic-receive-offload|large-receive-offload|generic-segmentation-offload|tcp-segmentation-offload'
```

**Expected output:**
```
generic-receive-offload: off
large-receive-offload: off [fixed]
generic-segmentation-offload: off
tcp-segmentation-offload: off
```

## Managing Services

### Check Status
```bash
sudo systemctl status orion-netsec-promisc.service
sudo systemctl status orion-netsec-nic-tuning.service
```

### Start Services
```bash
sudo systemctl start orion-netsec-promisc.service
sudo systemctl start orion-netsec-nic-tuning.service
```

### Stop Services
```bash
sudo systemctl stop orion-netsec-promisc.service
sudo systemctl stop orion-netsec-nic-tuning.service
```

### Enable on Boot
```bash
sudo systemctl enable orion-netsec-promisc.service
sudo systemctl enable orion-netsec-nic-tuning.service
```

### Disable on Boot
```bash
sudo systemctl disable orion-netsec-promisc.service
sudo systemctl disable orion-netsec-nic-tuning.service
```

### Restart Services
```bash
sudo systemctl restart orion-netsec-promisc.service
sudo systemctl restart orion-netsec-nic-tuning.service
```

### View Logs
```bash
sudo journalctl -u orion-netsec-promisc.service
sudo journalctl -u orion-netsec-nic-tuning.service

# Follow logs in real-time
sudo journalctl -u orion-netsec-promisc.service -f
```

## Troubleshooting

### Service Fails to Start
**Problem:** Service fails with error

**Check logs:**
```bash
sudo journalctl -u orion-netsec-promisc.service -n 50
```

**Common issues:**
1. **Interface doesn't exist:**
   ```
   Cannot find device "eth1"
   ```

   **Solution:** Check interface name with `ip link show` and update service file.
   Also verify NETSEC_INTERFACE in .env and --interface in ntopng.conf match.

2. **Permission denied:**
   ```
   Operation not permitted
   ```
   
   **Solution:** Ensure you're using `sudo` for all commands.

### Promiscuous Mode Not Persisting
**Problem:** Promiscuous mode disappears after reboot

**Solution:** Ensure service is enabled:
```bash
sudo systemctl enable orion-netsec-promisc.service
sudo systemctl is-enabled orion-netsec-promisc.service
```

Should output: `enabled`

### Offloads Not Disabled
**Problem:** ethtool shows offloads are still enabled

**Check if feature is supported:**
```bash
sudo ethtool -k eth1
```

Some offloads show `[fixed]` which means they cannot be changed by software. This is normal and not a problem.

**Note:** If you changed the interface from eth1, update the service file to match.

## Uninstallation

To remove the systemd units:

```bash
# Stop services
sudo systemctl stop orion-netsec-promisc.service
sudo systemctl stop orion-netsec-nic-tuning.service

# Disable services
sudo systemctl disable orion-netsec-promisc.service
sudo systemctl disable orion-netsec-nic-tuning.service

# Remove service files
sudo rm /etc/systemd/system/orion-netsec-promisc.service
sudo rm /etc/systemd/system/orion-netsec-nic-tuning.service

# Reload systemd
sudo systemctl daemon-reload

# Restore default NIC settings (if needed)
sudo ip link set eth1 promisc off
sudo ethtool -K eth1 gro on lro on gso on tso on
```

## Integration with Docker Compose

These systemd units run at the host level and are independent of Docker containers. They should be started before bringing up the NetSec tools:

```bash
# 1. Enable systemd units (one-time)
sudo systemctl enable orion-netsec-promisc.service
sudo systemctl start orion-netsec-promisc.service

# 2. Start Docker services
docker compose --profile netsec-minimal --profile netsec-tools up -d
```

The services will automatically start on boot, ensuring the network interface is properly configured before containers start.

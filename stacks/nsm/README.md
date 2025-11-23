# Orion Sentinel NSM Stack

Network Security Monitoring stack with Suricata IDS and log shipping.

## Overview

The NSM (Network Security Monitoring) stack provides:

- **Suricata IDS**: Passive network intrusion detection on mirrored traffic
- **Promtail**: Log shipping to central Loki instance

## Deployment Modes

### SPoG Mode (Normal Operation)

In production, the NetSec node acts as a sensor that sends logs to CoreSrv:

```
NetSec Node                          CoreSrv (Dell)
┌─────────────────┐                 ┌──────────────────┐
│ Suricata IDS    │                 │                  │
│       ↓         │                 │  Loki (central)  │
│   Promtail  ────┼────────────────→│  Grafana         │
└─────────────────┘   Logs (3100)   │  Dashboards      │
                                     └──────────────────┘
```

**Configuration**:

1. Set LOKI_URL in `.env` to point to CoreSrv:
   ```bash
   LOKI_URL=http://192.168.8.XXX:3100
   LOCAL_OBSERVABILITY=false
   ```

2. Start the stack:
   ```bash
   # Using helper script
   ../../scripts/netsecctl.sh up-spog
   
   # Or manually
   docker compose -f docker-compose.yml up -d
   ```

3. Verify logs are shipping:
   ```bash
   docker logs orion-promtail
   # Should see: POST /loki/api/v1/push (200 OK)
   ```

**Access**:
- View logs on CoreSrv Grafana: https://grafana.local
- Query: `{host="pi-netsec", job="suricata"}`

### Standalone/Lab Mode (Development)

For development and testing, run a local Loki + Grafana:

```
NetSec Node (Self-Contained)
┌─────────────────────────────┐
│ Suricata IDS                │
│       ↓                     │
│   Promtail                  │
│       ↓                     │
│   Loki (local)              │
│       ↓                     │
│   Grafana (local)           │
└─────────────────────────────┘
```

**Configuration**:

1. Set LOKI_URL in `.env` to local:
   ```bash
   LOKI_URL=http://loki:3100
   LOCAL_OBSERVABILITY=true
   ```

2. Start with local observability:
   ```bash
   # Using helper script
   ../../scripts/netsecctl.sh up-standalone
   
   # Or manually
   docker compose -f docker-compose.yml \
                  -f docker-compose.local-observability.yml up -d
   ```

**Access**:
- Local Grafana: http://localhost:3000 (admin/admin)
- Local Loki: http://localhost:3100

## Services

### Suricata

- **Image**: `jasonish/suricata:latest` (ARM-compatible)
- **Mode**: `host` network mode for packet capture
- **Interface**: Set via `NSM_IFACE` in `.env` (default: eth0)
- **Logs**: `/var/log/suricata/eve.json` (JSON events)

**Configuration**:
- Edit `suricata/suricata.yaml` for custom rules
- Update rules: Suricata auto-updates signatures

### Promtail

- **Image**: `grafana/promtail:2.9.3`
- **Purpose**: Ship Suricata logs to Loki
- **Destination**: Set via `LOKI_URL` environment variable

**Logs Shipped**:
- Suricata EVE JSON (alerts, flow, DNS, HTTP, etc.)
- Suricata application logs (errors/warnings only)

**Labels Applied**:
```
job: suricata
service: suricata
host: pi-netsec
log_type: nsm
event_type: <alert|flow|dns|http|...>
```

### Loki (Local - Dev Only)

Only runs when using `docker-compose.local-observability.yml`:

- **Image**: `grafana/loki:2.9.3`
- **Port**: 3100
- **Storage**: `loki-data` volume
- **Config**: `loki/loki-config.yaml`

### Grafana (Local - Dev Only)

Only runs when using `docker-compose.local-observability.yml`:

- **Image**: `grafana/grafana:10.2.3`
- **Port**: 3000
- **Credentials**: admin/admin (change on first login)
- **Datasource**: Auto-provisioned Loki

## Configuration Files

### Environment Variables (.env)

```bash
# Network interface for Suricata (set to mirrored/SPAN port)
NSM_IFACE=eth0

# Loki URL
# SPoG mode: http://192.168.8.XXX:3100 (CoreSrv IP)
# Dev mode: http://loki:3100
LOKI_URL=http://192.168.8.XXX:3100

# Local observability flag
# SPoG mode: false
# Dev mode: true
LOCAL_OBSERVABILITY=false

# Grafana password (dev mode only)
GRAFANA_ADMIN_PASSWORD=admin
```

### Suricata Configuration

Edit `suricata/suricata.yaml` to customize:

- Rule sources and categories
- Alert thresholds
- Output formats
- Performance tuning

### Promtail Configuration

Edit `promtail/promtail-config.yml` to customize:

- Log paths
- Label extraction
- Pipeline stages
- Filtering rules

## Network Setup

### Port Mirroring

Suricata requires mirrored network traffic. Configure your router/switch:

**Option 1: Switch Port Mirroring (SPAN)**

```
Switch Config:
  Source: LAN ports (all devices)
  Destination: NetSec node port
  Direction: Ingress + Egress
```

**Option 2: Router Port Mirroring**

Many routers (GL.iNet, pfSense, OpenWrt) support traffic mirroring to a specific port.

**Option 3: Network TAP**

Use a physical network TAP between router and switch.

### Verify Traffic Capture

```bash
# Check Suricata is seeing traffic
docker logs orion-suricata | grep "captured"

# Check for alerts
docker exec orion-suricata tail -f /var/log/suricata/eve.json | grep alert
```

## Monitoring

### Check Service Status

```bash
# Using helper script
../../scripts/netsecctl.sh status

# Or manually
docker compose ps
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker logs -f orion-suricata
docker logs -f orion-promtail
```

### Verify Log Shipping

```bash
# Check Promtail is pushing to Loki
docker logs orion-promtail | grep "POST"

# Should see:
# level=info msg="POST /loki/api/v1/push (200 OK)"
```

## Troubleshooting

### Suricata Not Capturing Traffic

1. Check network interface:
   ```bash
   docker exec orion-suricata ip link
   ```

2. Verify NSM_IFACE in `.env` matches your mirrored port

3. Check port mirroring is configured on switch/router

4. Verify Suricata is running:
   ```bash
   docker logs orion-suricata | grep "all 1 packet processing threads"
   ```

### Promtail Not Shipping Logs

1. Check LOKI_URL connectivity:
   ```bash
   # From NetSec node
   curl http://192.168.8.XXX:3100/ready
   # Should return: 200 OK
   ```

2. Check Promtail logs for errors:
   ```bash
   docker logs orion-promtail | grep error
   ```

3. Verify Suricata is generating logs:
   ```bash
   docker exec orion-suricata ls -lh /var/log/suricata/eve.json
   ```

### No Data in Grafana (Standalone Mode)

1. Verify Loki is running:
   ```bash
   curl http://localhost:3100/ready
   ```

2. Check Promtail is configured correctly:
   ```bash
   docker logs orion-promtail | grep "clients configured"
   ```

3. Query Loki directly:
   ```bash
   curl -G http://localhost:3100/loki/api/v1/query \
     --data-urlencode 'query={job="suricata"}' \
     --data-urlencode 'limit=10'
   ```

## Performance Tuning

### Suricata

For high-traffic networks, tune Suricata in `suricata.yaml`:

```yaml
# Increase worker threads (max = CPU cores)
threading:
  set-cpu-affinity: yes
  cpu-affinity:
    - management-cpu-set:
        cpu: [0]
    - receive-cpu-set:
        cpu: [1]
    - worker-cpu-set:
        cpu: [2-3]

# Adjust buffer sizes
af-packet:
  - interface: eth0
    buffer-size: 64535
    ring-size: 2048
```

### Loki (Standalone Mode)

For longer retention, edit `loki/loki-config.yaml`:

```yaml
limits_config:
  retention_period: 168h  # 7 days (default)

chunk_store_config:
  max_look_back_period: 168h
```

## Integration with AI Stack

The AI stack reads Suricata logs from Loki for threat detection:

```
NSM Stack                    AI Stack
┌──────────────┐            ┌──────────────────┐
│  Suricata    │            │                  │
│      ↓       │            │  AI Services     │
│  Promtail    │────────────→  (read from      │
│      ↓       │  via Loki  │   Loki)          │
│   Loki   ────┼───────────→│                  │
└──────────────┘            └──────────────────┘
```

AI services query Loki for:
- Suricata alerts: `{job="suricata", event_type="alert"}`
- DNS logs: `{job="suricata", event_type="dns"}`
- Flow data: `{job="suricata", event_type="flow"}`

## Related Documentation

- [CoreSrv Integration](../../docs/CORESRV-INTEGRATION.md) - Integrate with CoreSrv SPoG
- [Architecture](../../docs/architecture.md) - System architecture
- [AI Stack](../ai/README.md) - AI detection services
- [Suricata Documentation](https://suricata.readthedocs.io/) - Official Suricata docs

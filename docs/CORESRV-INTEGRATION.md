# CoreSrv Integration Guide

This document explains how to integrate the Orion Sentinel NetSec node with the CoreSrv (Dell) Single Pane of Glass (SPoG) platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      CoreSrv (Dell SPoG)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Traefik + Authelia (SSO & Reverse Proxy)               │  │
│  │  - https://security.local → NetSec UI                    │  │
│  │  - https://grafana.local → Grafana                       │  │
│  │  - https://prometheus.local → Prometheus                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Central Monitoring Stack                                │  │
│  │  - Loki (3100) ← receives logs from NetSec              │  │
│  │  - Prometheus (9090) ← scrapes NetSec metrics           │  │
│  │  - Grafana (3000) ← dashboards for all nodes            │  │
│  │  - Uptime-Kuma (3001) ← status monitoring               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ Logs & Metrics
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                    NetSec Node (Pi 5)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NSM Stack                                               │  │
│  │  - Suricata IDS → Promtail → CoreSrv Loki              │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  AI Stack                                                │  │
│  │  - AI Services → CoreSrv Loki (via LOKI_URL)           │  │
│  │  - Web UI (8000) ← proxied by CoreSrv Traefik          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## NetSec Configuration

### 1. Configure LOKI_URL

Edit `.env` on the NetSec node:

```bash
# Point to CoreSrv Loki (replace XXX with CoreSrv IP)
LOKI_URL=http://192.168.8.XXX:3100

# Disable local observability
LOCAL_OBSERVABILITY=false
```

### 2. Start NetSec in SPoG Mode

```bash
# Using the helper script
./scripts/netsecctl.sh up-spog

# Or manually
cd stacks/nsm
docker compose -f docker-compose.yml up -d

cd ../ai
docker compose up -d
```

### 3. Verify Log Shipping

Check that Promtail is shipping logs to CoreSrv:

```bash
# Check Promtail logs
docker logs orion-promtail

# Should see successful pushes to CoreSrv Loki
# Example: "POST /loki/api/v1/push (200 OK)"
```

### 4. Verify AI Services Connection

Check that AI services can connect to CoreSrv Loki:

```bash
# Check SOAR service logs
docker logs orion-soar

# Check inventory service logs
docker logs orion-inventory

# Look for: "Initialized LokiClient with URL: http://192.168.8.XXX:3100"
```

## CoreSrv Configuration

These configurations should be applied on the CoreSrv (Dell) side, in the `Orion-Sentinel-CoreSrv` repository.

### 1. Expose Loki Port (Optional)

By default, Loki runs on CoreSrv's internal network. To allow NetSec to push logs:

**Option A: Expose Loki port directly** (simpler, suitable for trusted LAN):

In `monitoring/docker-compose.yml` on CoreSrv:

```yaml
services:
  loki:
    ports:
      - "3100:3100"  # Allow NetSec to push logs
```

**Option B: Use Promtail on NetSec with Docker socket** (more secure):

Keep Loki internal and use Docker remote logging driver (not covered here).

### 2. Traefik Route for NetSec Web UI

Add this to CoreSrv's Traefik dynamic configuration (e.g., `core/traefik/dynamic/netsec.yml`):

```yaml
http:
  routers:
    orion-security:
      rule: "Host(`security.local`)"
      entryPoints:
        - websecure
      tls: true
      middlewares:
        - secure-chain@file
      service: orion-security-svc

  services:
    orion-security-svc:
      loadBalancer:
        servers:
          - url: "http://192.168.8.241:8000"  # Replace with NetSec node IP
```

Replace `192.168.8.241` with your NetSec node's LAN IP.

### 3. Prometheus Scrape Configuration

Add NetSec node metrics to CoreSrv's Prometheus config (`monitoring/prometheus/prometheus.yml`):

```yaml
scrape_configs:
  # ... existing jobs ...

  - job_name: "pi-netsec"
    static_configs:
      - targets:
          - "192.168.8.241:9100"  # node_exporter (if installed)
        labels:
          node: "pi-netsec"
          role: "security-sensor"
```

### 4. Import NetSec Dashboards

1. Copy Grafana dashboards from NetSec repo to CoreSrv:

```bash
# On CoreSrv
cd /srv/orion-sentinel-core
cp /path/to/netsec/grafana/dashboards/*.json \
   monitoring/grafana/dashboards/orion/
```

2. Restart Grafana to pick up new dashboards:

```bash
docker compose -f monitoring/docker-compose.yml restart grafana
```

## Access NetSec Services via CoreSrv

Once configured, access NetSec services through CoreSrv's Traefik:

- **NetSec Web UI**: https://security.local (via Traefik + Authelia SSO)
- **NetSec Logs**: https://grafana.local → Explore → select "Loki" → `{host="pi-netsec"}`
- **NetSec Metrics**: https://prometheus.local → Targets → "pi-netsec"

## Network Requirements

Ensure network connectivity between CoreSrv and NetSec:

1. **CoreSrv Loki accessible from NetSec**:
   - Test: `curl http://192.168.8.XXX:3100/ready` from NetSec
   - Should return: 200 OK

2. **NetSec Web UI accessible from CoreSrv**:
   - Test: `curl http://192.168.8.241:8000/api/health` from CoreSrv
   - Should return: JSON health status

3. **Firewall Rules** (if applicable):
   - Allow CoreSrv → NetSec:8000 (Web UI)
   - Allow NetSec → CoreSrv:3100 (Loki)
   - Allow CoreSrv → NetSec:9100 (node_exporter, if used)

## Troubleshooting

### Logs Not Appearing on CoreSrv

1. Check Promtail on NetSec:
   ```bash
   docker logs orion-promtail
   ```
   Look for connection errors to CoreSrv Loki.

2. Verify LOKI_URL in NetSec `.env`:
   ```bash
   grep LOKI_URL .env
   ```

3. Test connectivity to CoreSrv Loki:
   ```bash
   curl http://192.168.8.XXX:3100/ready
   ```

4. Check CoreSrv Loki logs:
   ```bash
   docker logs orion-loki
   ```

### NetSec Web UI Not Accessible via security.local

1. Verify Traefik route is configured on CoreSrv
2. Check DNS resolution:
   ```bash
   ping security.local
   ```
   Should resolve to CoreSrv IP.

3. Check Traefik logs on CoreSrv:
   ```bash
   docker logs traefik
   ```

4. Verify NetSec web UI is running:
   ```bash
   docker logs orion-api
   curl http://192.168.8.241:8000
   ```

### AI Services Can't Connect to Loki

1. Check LOKI_URL environment variable:
   ```bash
   docker exec orion-soar env | grep LOKI_URL
   ```

2. Verify network connectivity:
   ```bash
   docker exec orion-soar curl http://192.168.8.XXX:3100/ready
   ```

3. Check AI service logs:
   ```bash
   docker logs orion-soar
   docker logs orion-inventory
   ```

## Development/Lab Mode

To run NetSec standalone with local observability (for development):

```bash
# Edit .env
LOKI_URL=http://loki:3100
LOCAL_OBSERVABILITY=true

# Start with local Loki+Grafana
./scripts/netsecctl.sh up-standalone

# Access local services
# Grafana: http://localhost:3000
# NetSec UI: http://localhost:8000
```

This is useful for:
- Development and testing
- Debugging AI models
- Offline operation
- Lab environments without CoreSrv

## Security Considerations

1. **Authelia SSO**: NetSec web UI is protected by Authelia when accessed via `security.local`
2. **TLS**: All access via Traefik uses HTTPS (except direct LAN access for development)
3. **Network Isolation**: NetSec and CoreSrv should be on a trusted LAN, not exposed to internet
4. **API Authentication**: Consider adding API keys if exposing services beyond local network

## Related Documentation

- [CoreSrv Integration](https://github.com/yorgosroussakis/Orion-Sentinel-CoreSrv) - CoreSrv repository
- [NetSec Quickstart](../QUICKSTART.md) - NetSec setup guide
- [Architecture Overview](architecture.md) - Detailed architecture
- [Grafana Dashboards](../grafana/dashboards/README.md) - Dashboard documentation

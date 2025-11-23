# Quick Start Guide

This is a condensed version of the setup instructions for Orion Sentinel NetSec node.

## Choose Your Deployment Mode

### 🎯 SPoG Mode (Production - Recommended)

NetSec node as a sensor reporting to CoreSrv for centralized observability.

**Prerequisites:**
- CoreSrv (Dell) with Loki running and accessible on LAN
- Raspberry Pi 5 (8GB) or mini-PC with Docker installed
- Network switch with port mirroring (SPAN) configured
- Pi-hole instance (optional, for DNS blocking)

**Quick Setup:**

```bash
# 1. Clone repository
git clone https://github.com/yorgosroussakis/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai

# 2. Configure environment
cp .env.example .env
nano .env

# Set these critical values:
# LOKI_URL=http://192.168.8.XXX:3100  # Your CoreSrv IP
# LOCAL_OBSERVABILITY=false
# NSM_IFACE=eth0  # Your mirrored port interface

# 3. Start in SPoG mode
./scripts/netsecctl.sh up-spog

# 4. Verify log shipping
docker logs orion-promtail | grep "POST"
# Should see: POST /loki/api/v1/push (200 OK)
```

**Access:**
- Dashboards: https://grafana.local (on CoreSrv)
- NetSec Web UI: https://security.local (via CoreSrv Traefik)
- Logs in Grafana: `{host="pi-netsec"}`

**Next Steps:**
- See [CoreSrv Integration Guide](docs/CORESRV-INTEGRATION.md) for Traefik setup
- Configure SOAR playbooks in `stacks/ai/config/playbooks.yml`
- Set up notifications (Email, Signal, Telegram) in `.env`

---

### 🧪 Standalone Mode (Development/Lab)

NetSec node with local Loki + Grafana for development and testing.

**Prerequisites:**
- Raspberry Pi 5 (8GB) or mini-PC with Docker installed
- Network switch with port mirroring (SPAN) configured

**Quick Setup:**

```bash
# 1. Clone repository
git clone https://github.com/yorgosroussakis/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai

# 2. Configure environment
cp .env.example .env
nano .env

# Set these values:
# LOKI_URL=http://loki:3100
# LOCAL_OBSERVABILITY=true
# NSM_IFACE=eth0

# 3. Start in standalone mode
./scripts/netsecctl.sh up-standalone

# 4. Verify services
docker compose -f stacks/nsm/docker-compose.yml ps
docker compose -f stacks/ai/docker-compose.yml ps
```

**Access:**
- Grafana: http://localhost:3000 (admin/admin)
- NetSec Web UI: http://localhost:8000
- Loki API: http://localhost:3100

---

## Common Operations

### Using netsecctl.sh Helper Script

```bash
# Check service status
./scripts/netsecctl.sh status

# View logs
./scripts/netsecctl.sh logs

# Stop all services
./scripts/netsecctl.sh down

# Get help
./scripts/netsecctl.sh help
```

### Manual Docker Compose Commands

**SPoG Mode:**
```bash
# Start NSM (Suricata + Promtail)
cd stacks/nsm
docker compose up -d

# Start AI services
cd ../ai
docker compose up -d
```

**Standalone Mode:**
```bash
# Start NSM with local Loki+Grafana
cd stacks/nsm
docker compose -f docker-compose.yml -f docker-compose.local-observability.yml up -d

# Start AI services
cd ../ai
docker compose up -d
```

## Verification Steps

### 1. Check Suricata Traffic Capture

```bash
# View Suricata logs
docker logs orion-suricata | tail -20

# Check for traffic capture
docker exec orion-suricata tail -f /var/log/suricata/eve.json
# Should see JSON events scrolling
```

### 2. Verify Log Shipping (SPoG Mode)

```bash
# Check Promtail is pushing to CoreSrv
docker logs orion-promtail | grep "POST"

# Test CoreSrv Loki connectivity
curl http://192.168.8.XXX:3100/ready
# Should return: 200 OK
```

### 3. Check AI Services

```bash
# Verify LOKI_URL is set correctly
docker exec orion-soar env | grep LOKI_URL

# Check service logs
docker logs orion-soar
docker logs orion-inventory
docker logs orion-health-score
```

### 4. Test Web UI

```bash
# SPoG mode (via CoreSrv Traefik)
curl https://security.local/api/health

# Standalone mode
curl http://localhost:8000/api/health
# Should return JSON health status
```

## Network Setup

### Configure Port Mirroring

Your network switch must mirror traffic to the NetSec node:

**Example (Managed Switch):**
1. Access switch management interface
2. Configure port mirroring:
   - Source: All LAN ports
   - Destination: Port connected to NetSec node
   - Direction: Both (ingress + egress)

**Verify Interface:**
```bash
# List network interfaces
ip link show

# Set NSM_IFACE in .env to your mirrored port
# Example: eth0, eth1, enp1s0, etc.
```

## Troubleshooting

### No Traffic in Suricata

1. Verify port mirroring is configured correctly on switch
2. Check NSM_IFACE in `.env` matches your physical interface
3. Run: `docker exec orion-suricata ip link` to see available interfaces

### Logs Not Appearing on CoreSrv (SPoG Mode)

1. Test Loki connectivity: `curl http://coresrv-ip:3100/ready`
2. Check LOKI_URL in `.env`
3. View Promtail logs: `docker logs orion-promtail`
4. Verify CoreSrv Loki port 3100 is open

### Services Won't Start

1. Check Docker is running: `docker info`
2. Verify `.env` file exists in project root
3. Check for port conflicts: `docker compose ps`
4. View service logs: `docker logs <container-name>`

## Next Steps

- **Configure SOAR**: Edit `stacks/ai/config/playbooks.yml`
- **Set up Notifications**: Configure Email/Signal/Telegram in `.env`
- **Enable Threat Intel**: Get API keys for OTX, URLhaus, etc.
- **Create Dashboards**: Import dashboards to CoreSrv Grafana
- **Test SOAR**: Run in dry-run mode first (`SOAR_DRY_RUN=1`)

## Documentation

- [CoreSrv Integration](docs/CORESRV-INTEGRATION.md) - Full SPoG setup guide
- [NSM Stack](stacks/nsm/README.md) - Suricata and Promtail details
- [AI Stack](stacks/ai/README.md) - AI services configuration
- [Architecture](docs/architecture.md) - System design overview

For detailed documentation, see the [main README](README.md) and `docs/` directory.
cd ../ai

# IMPORTANT: Place your ML models in ./models/ directory first
# See models/README.md for details

docker compose up -d

# Check AI service logs
docker compose logs orion-ai

# Test AI service API (if running in API mode)
curl http://localhost:8080/health
```

## 4. Configure DNS Log Shipping (on Pi #1)

Follow instructions in `docs/integration-orion-dns-ha.md` to configure Pi #1 to ship DNS logs to this Pi.

## 5. Verify Everything Works

### Check Loki has data
```bash
# Query Suricata logs
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="suricata"}' | jq

# Query DNS logs (if Pi #1 is configured)
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="pihole"}' | jq
```

### Check Grafana
1. Open http://pi2-ip:3000
2. Go to Explore
3. Select Loki datasource
4. Run query: `{service="suricata"}`
5. You should see Suricata events

### Check AI Detection
```bash
# Trigger manual detection (if AI service is running)
curl -X POST "http://localhost:8080/api/v1/detect/device?minutes_ago=10"
curl -X POST "http://localhost:8080/api/v1/detect/domain?minutes_ago=60"
```

## Common Issues

### Suricata not capturing traffic
- Check `NSM_IFACE` is correct in `.env`
- Verify interface is up: `ip link show`
- Verify port mirroring is configured on switch
- Check with tcpdump: `sudo tcpdump -i eth0 -c 100`

### Loki out of disk space
- Reduce `LOKI_RETENTION_DAYS` in `.env`
- Check disk usage: `df -h`
- Clean old data: `docker compose stop loki && rm -rf loki/data/* && docker compose start loki`

### AI service cannot read logs
- Check Loki is accessible: `docker compose exec orion-ai curl http://loki:3100/ready`
- Verify logs exist in Loki (use Grafana Explore)
- Check AI service logs: `docker compose logs orion-ai`

### DNS logs not appearing
- On Pi #1: Check Promtail is running and configured correctly
- On Pi #2: Check firewall allows port 3100 from Pi #1
- Test connectivity: `curl http://pi2-ip:3100/ready` (from Pi #1)

## Next Steps

1. Create Grafana dashboards (see `docs/logging-and-dashboards.md`)
2. Fine-tune Suricata rules
3. Train or obtain AI models (see `stacks/ai/models/README.md`)
4. Set up alerting in Grafana
5. Review and adjust detection thresholds

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project overview and features |
| [docs/architecture.md](docs/architecture.md) | Detailed system architecture |
| [docs/pi2-setup.md](docs/pi2-setup.md) | Complete setup guide |
| [docs/logging-and-dashboards.md](docs/logging-and-dashboards.md) | Loki queries and Grafana dashboards |
| [docs/ai-stack.md](docs/ai-stack.md) | AI service design and models |
| [docs/integration-orion-dns-ha.md](docs/integration-orion-dns-ha.md) | Pi #1 integration |

## Getting Help

- Check logs: `docker compose logs <service-name>`
- Review documentation in `docs/`
- Check GitHub issues
- Verify prerequisites are met

---

**Remember**: This is a passive monitoring system. Pi #2 does NOT route traffic and cannot impact your network if it fails.

# Quick Start Guide

This is a condensed version of the setup instructions. For detailed documentation, see the `docs/` directory.

## Prerequisites

- Raspberry Pi 5 (8 GB RAM recommended)
- Raspberry Pi AI Hat (optional but recommended)
- Raspberry Pi OS 64-bit (Debian Bookworm or later)
- Docker & Docker Compose installed
- Network switch with port mirroring capability
- Access to Pi #1's Pi-hole API (from orion-sentinel-dns-ha repo)

## 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/orion-sentinel-nsm-ai.git
cd orion-sentinel-nsm-ai

# Configure NSM stack
cd stacks/nsm
cp .env.example .env
nano .env  # Edit NSM_IFACE and other settings

# Configure AI stack
cd ../ai
cp .env.example .env
nano .env  # Edit Pi-hole API URL, token, and thresholds
cd ../..
```

## 2. Deploy NSM Stack

```bash
cd stacks/nsm
docker compose up -d

# Verify services are running
docker compose ps

# Check Suricata is capturing traffic
docker compose logs suricata | tail -20

# Access Grafana at http://pi2-ip:3000 (admin/admin)
```

## 3. Deploy AI Service

```bash
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

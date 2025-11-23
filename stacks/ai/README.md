# Orion Sentinel AI Stack

AI-powered threat detection and SOAR automation services.

## Overview

The AI stack provides intelligent threat detection, correlation, and automated response capabilities:

- **SOAR Service**: Security orchestration and automated response
- **Inventory Service**: Device discovery and tracking
- **Health Score Service**: Network security health monitoring
- **Change Monitor**: Baseline and anomaly detection
- **Web UI/API**: Dashboard and REST API

## Deployment Modes

### SPoG Mode (Normal Operation)

In production, AI services connect to CoreSrv Loki for log reading/writing:

```
AI Services (NetSec)          CoreSrv (Dell)
┌──────────────────┐         ┌──────────────────┐
│ SOAR             │         │                  │
│ Inventory        │────────→│  Loki (central)  │
│ Health Score     │ Queries │  (read/write)    │
│ Change Monitor   │         │                  │
│ Web UI/API       │         └──────────────────┘
└──────────────────┘
```

**Configuration**:

Set LOKI_URL in `.env` to point to CoreSrv:
```bash
LOKI_URL=http://192.168.8.XXX:3100  # CoreSrv IP
```

All AI services will automatically use this central Loki instance.

### Standalone/Lab Mode (Development)

For development and testing, use local Loki from NSM stack:

```bash
LOKI_URL=http://loki:3100
LOCAL_OBSERVABILITY=true
```

This requires the NSM stack to be running with local observability enabled.

## Services

### SOAR (Security Orchestration & Automated Response)

- **Container**: `orion-soar`
- **Purpose**: Execute playbooks based on security events
- **Config**: `config/playbooks.yml`

**Key Environment Variables**:
- `SOAR_DRY_RUN`: Enable dry-run mode (default: 1)
- `SOAR_POLL_INTERVAL`: Event polling interval in seconds (default: 60)
- `PIHOLE_URL`: Pi-hole instance for DNS blocking
- `PIHOLE_API_KEY`: Pi-hole API key

**Playbook Actions**:
- Block domains via Pi-hole
- Send notifications (Email, Signal, Telegram, Webhook)
- Tag devices
- Execute custom scripts

See [SOAR Documentation](../../docs/soar.md) for details.

### Inventory Service

- **Container**: `orion-inventory`
- **Purpose**: Device discovery and tracking from network logs
- **Storage**: SQLite database in `/data/inventory.db`

**Key Environment Variables**:
- `INVENTORY_POLL_INTERVAL`: Collection interval in seconds (default: 300)

Automatically discovers devices from:
- Suricata flow logs
- DNS queries
- DHCP logs (if available)

### Health Score Service

- **Container**: `orion-health-score`
- **Purpose**: Calculate overall network security health
- **Interval**: Every hour (configurable)

**Key Environment Variables**:
- `HEALTH_SCORE_INTERVAL_HOURS`: Calculation interval (default: 1)

Health score (0-100) based on:
- Recent alerts and severity
- Device anomalies
- DNS security (blocked queries)
- Threat intelligence hits

### Change Monitor

- **Container**: `orion-change-monitor`
- **Purpose**: Detect changes in network behavior
- **Storage**: Baseline data in `/data`

**Key Environment Variables**:
- `CHANGE_MONITOR_INTERVAL_HOURS`: Check interval (default: 24)
- `CHANGE_MONITOR_PERIOD_DAYS`: Analysis period (default: 7)

Monitors changes in:
- Active devices
- Traffic patterns
- DNS queries
- Port usage

### Web UI / API Server

- **Container**: `orion-api`
- **Port**: 8000
- **Purpose**: Web dashboard and REST API

**Access**:
- **SPoG Mode**: https://security.local (via CoreSrv Traefik)
- **Standalone Mode**: http://localhost:8000

**Endpoints**:
- `/` - Dashboard
- `/events` - Security events log
- `/devices` - Device inventory
- `/playbooks` - SOAR playbook management
- `/api/` - REST API (JSON)
- `/docs` - OpenAPI/Swagger documentation

**Key Environment Variables**:
- `API_HOST`: Bind address (default: 0.0.0.0)
- `API_PORT`: Port (default: 8000)

## Configuration

### Environment Variables

All services read from `.env` in the project root. Key settings:

```bash
# Loki Connection
LOKI_URL=http://192.168.8.XXX:3100  # CoreSrv Loki

# SOAR
SOAR_DRY_RUN=1
SOAR_POLL_INTERVAL=60

# Notifications
NOTIFY_SMTP_HOST=smtp.gmail.com
NOTIFY_SMTP_PORT=587
NOTIFY_SMTP_USER=
NOTIFY_SMTP_PASS=

# Threat Intelligence
TI_ENABLE_OTX=true
TI_OTX_API_KEY=

# Pi-hole
PIHOLE_URL=http://192.168.1.2
PIHOLE_API_KEY=
```

See [.env.example](../../.env.example) for all options.

### Playbooks

Edit `config/playbooks.yml` to configure SOAR automation:

```yaml
playbooks:
  - name: alert-high-risk-domain
    enabled: true
    trigger:
      event_type: domain_risk
      min_confidence: 0.9
    actions:
      - type: block_domain
        domain: "{{domain}}"
      - type: notify
        message: "Blocked high-risk domain: {{domain}}"
```

See [SOAR Documentation](../../docs/soar.md) for playbook syntax.

## Deployment

### Using Helper Script (Recommended)

```bash
# SPoG mode (production)
../../scripts/netsecctl.sh up-spog

# Standalone mode (development)
../../scripts/netsecctl.sh up-standalone
```

### Manual Docker Compose

```bash
# Start AI services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Integration with NSM Stack

The AI stack reads Suricata logs from Loki (via NSM stack):

```
NSM Stack              AI Stack
┌──────────┐          ┌──────────────────┐
│ Suricata │          │                  │
│    ↓     │          │  AI Services     │
│ Promtail │          │  ↓               │
│    ↓     │          │  Query Loki for: │
│  Loki    │←─────────│  - Alerts        │
│          │  LogQL   │  - DNS logs      │
└──────────┘          │  - Flow data     │
                      └──────────────────┘
```

**LogQL Queries Used**:
- Alerts: `{job="suricata", event_type="alert"}`
- DNS: `{job="suricata", event_type="dns"}`
- Flows: `{job="suricata", event_type="flow"}`

## Monitoring

### Service Health

```bash
# Check all services
docker compose ps

# View specific service logs
docker logs orion-soar
docker logs orion-inventory
docker logs orion-health-score
```

### API Health Check

```bash
# SPoG mode
curl https://security.local/api/health

# Standalone mode
curl http://localhost:8000/api/health
```

## Troubleshooting

### Services Can't Connect to Loki

1. Verify LOKI_URL in `.env`:
   ```bash
   grep LOKI_URL .env
   ```

2. Test Loki connectivity:
   ```bash
   docker exec orion-soar curl http://192.168.8.XXX:3100/ready
   ```

3. Check service logs:
   ```bash
   docker logs orion-soar | grep -i loki
   ```

### SOAR Not Executing Actions

1. Check dry-run mode:
   ```bash
   grep SOAR_DRY_RUN .env
   # Should be 0 for actual execution
   ```

2. Verify playbooks are loaded:
   ```bash
   docker logs orion-soar | grep playbook
   ```

3. Check for events:
   ```bash
   curl http://localhost:8000/api/events?limit=10
   ```

### Web UI Not Accessible

1. Check API service is running:
   ```bash
   docker logs orion-api
   ```

2. Verify port binding:
   ```bash
   docker compose ps | grep api
   # Should show 8000:8000
   ```

3. Test locally:
   ```bash
   curl http://localhost:8000
   ```

## Development

### Running Services Locally

```bash
# Install dependencies
pip install -r ../../requirements-dev.txt

# Run individual service
cd ../..
python -m orion_ai.soar.service
python -m orion_ai.inventory.service
```

### Building Docker Image

```bash
# Build image
docker compose build

# Build with no cache
docker compose build --no-cache
```

## Related Documentation

- [CoreSrv Integration](../../docs/CORESRV-INTEGRATION.md) - Integration with CoreSrv SPoG
- [SOAR Documentation](../../docs/soar.md) - Playbook configuration
- [Notifications](../../docs/notifications.md) - Alert configuration
- [Threat Intelligence](../../docs/threat-intel.md) - Threat intel feeds
- [Web UI](../../docs/web-ui.md) - Web dashboard guide

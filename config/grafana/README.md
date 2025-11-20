# Grafana SOC Dashboards

This directory contains Grafana dashboard configurations and provisioning files for the Orion Sentinel SOC platform.

## Dashboards

### SOC Management Dashboard (`soc-management.json`)

Comprehensive executive dashboard showing:

**Security Health**
- Overall health score gauge (0-100)
- Health score trend over time
- Component scores breakdown
- Actionable recommendations

**Key Metrics (24h)**
- Total devices
- Threat intel matches
- AI anomalies detected
- SOAR actions executed
- High-risk changes
- New devices (7d)
- Honeypot hits
- Suricata alerts

**Event Analysis**
- Events by service (pie chart)
- Security events by severity (time series)

**Activity Logs**
- Recent SOAR actions
- Recent threat intel matches
- High-risk change events

## Provisioning

Dashboards are automatically loaded via Grafana provisioning:

- **Datasources**: `datasources/loki.yml` - Loki connection
- **Dashboards**: `dashboards/dashboards.yml` - Dashboard provider config
- **Dashboard Files**: `dashboards/*.json` - Dashboard definitions

## Access

After starting the stack:

```bash
cd stacks/ai && docker-compose up -d
```

Access Grafana at: http://localhost:3000

**Default Credentials**:
- Username: `admin`
- Password: Set via `GRAFANA_ADMIN_PASSWORD` env var (default: `admin`)

## Dashboard Features

### Auto-Refresh

Dashboard refreshes every 30 seconds to show real-time data.

### Time Range

Default view: Last 24 hours

Adjust using Grafana's time picker in the top-right.

### Panels

1. **Health Score Gauge** - Current security posture (0-100)
2. **Service Distribution** - Event volume by service
3. **Threat Counters** - Key security metrics
4. **Trend Charts** - Historical analysis
5. **Log Panels** - Recent events with details

## Customization

Dashboards are editable through Grafana UI:

1. Open dashboard
2. Click panel title → Edit
3. Modify queries, visualization, thresholds
4. Save dashboard

Changes persist in Grafana's database.

## Log Queries

Dashboards use LogQL to query Loki:

```logql
# Health score
{service="health_score"} | json | score

# Threat intel matches
{service="threat_intel", stream="intel_match"}

# SOAR actions
{service="soar", stream="soar_action"}

# High-risk changes
{service="change_monitor", risk_level=~"high|critical"}
```

## Integration with DNS Repo

For DNS metrics from the `orion-sentinel-dns-ha` repository:

1. Ensure DNS logs are forwarded to Loki with label `service="dns"`
2. Pi-hole metrics with label `service="pihole"`
3. Queries will automatically include these sources

Example DNS queries:
```logql
# DNS queries
{service="dns"} | json | query_name

# Pi-hole blocks
{service="pihole"} | json | status="blocked"
```

## Troubleshooting

### Dashboard not loading

1. Check Grafana logs: `docker logs orion-grafana`
2. Verify Loki is running: `docker ps | grep loki`
3. Test Loki connection: `curl http://localhost:3100/ready`

### No data in panels

1. Verify services are logging to Loki
2. Check time range (default: 24h)
3. Confirm LogQL queries match your log labels
4. Test queries in Grafana's Explore view

### Permission issues

Ensure Grafana provisioning directory is readable:
```bash
chmod -R 755 config/grafana/provisioning
```

## Adding New Dashboards

1. Create JSON file in `config/grafana/provisioning/dashboards/`
2. Grafana will auto-load on next restart
3. Or use Grafana UI to create, then export JSON

## Performance

- Dashboards optimized for Raspberry Pi 5
- Limited to 1000 log lines per query
- 30-second refresh interval balances freshness vs. load
- Adjust `maxLines` in datasource config if needed

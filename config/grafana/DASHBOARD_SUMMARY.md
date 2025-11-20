# Grafana Dashboard Summary

## Created Dashboards

### 1. SOC Management Dashboard
**File**: `config/grafana/provisioning/dashboards/soc-management.json`
**UID**: `orion-soc-mgmt`

#### Panels (16 total):

**Executive Overview:**
1. Security Health Score - Gauge (0-100 with color thresholds)
2. Events by Service (24h) - Pie chart
3. Total Devices - Stat panel
4. Threat Intel Matches (24h) - Stat panel (threshold: yellow@1, red@5)
5. AI Anomalies (24h) - Stat panel (threshold: yellow@5, red@10)
6. SOAR Actions (24h) - Stat panel (threshold: yellow@1, red@3)

**Detailed Metrics:**
7. High-Risk Changes (24h) - Stat panel (threshold: yellow@5, red@10)
8. New Devices (7d) - Stat panel (threshold: yellow@1)
9. Honeypot Hits (24h) - Stat panel (threshold: red@1)
10. Suricata Alerts (24h) - Stat panel (threshold: yellow@10, red@50)

**Trend Analysis:**
11. Security Health Score Trend - Time series chart
12. Security Events by Severity - Stacked bar chart

**Activity Logs:**
13. Recent SOAR Actions - Log panel
14. Recent Threat Intel Matches - Log panel
15. High-Risk Change Events - Log panel
16. Health Score Recommendations - Table

### 2. DNS & Pi-hole Dashboard
**File**: `config/grafana/provisioning/dashboards/dns-pihole.json`
**UID**: `orion-dns`

#### Panels (10 total):

**Key Metrics:**
1. DNS Queries (1h) - Stat with area graph
2. Pi-hole Blocks (1h) - Stat with area graph (red if > 0)
3. DNS Query Status Distribution - Donut chart (allowed vs blocked)
4. Top 10 Queried Domains - Pie chart
5. Active DNS Clients - Stat counter
6. Block Rate % - Gauge (green < 50%, yellow < 80%, red ≥ 80%)

**Analysis:**
7. DNS Query Rate Over Time - Time series (green=allowed, red=blocked)
8. Top Blocked Domains - Table (top 20)
9. Top DNS Clients by Query Volume - Table (top 20)
10. Recent Blocked Queries - Log panel

## Integration Points

### Loki Queries Used:

**SOC Dashboard:**
```logql
# Health score
{service="health_score"} | json | score

# Service events
sum by (service) (count_over_time({service=~"soar|inventory|health_score|change_monitor"}[24h]))

# Threat intel
sum(count_over_time({service="threat_intel", stream="intel_match"}[24h]))

# AI anomalies
sum(count_over_time({service="ai", stream=~"ai-device-anomaly|ai-domain-risk"}[24h]))

# SOAR actions
sum(count_over_time({service="soar", stream="soar_action", executed="true"}[24h]))

# High-risk changes
sum(count_over_time({service="change_monitor", risk_level="high"}[24h]))

# Honeypot hits
sum(count_over_time({service="honeypot"}[24h]))

# Suricata alerts
sum(count_over_time({service="suricata", event_type="alert"}[24h]))
```

**DNS Dashboard:**
```logql
# DNS queries
sum(count_over_time({service="dns"}[1h]))

# Pi-hole blocks
sum(count_over_time({service="pihole", status="blocked"}[1h]))

# Status distribution
sum by (status) (count_over_time({service="pihole"}[24h]))

# Top domains
topk(10, sum by (query_name) (count_over_time({service="dns"}[24h])))

# Block rate
(sum(count_over_time({service="pihole", status="blocked"}[1h])) / sum(count_over_time({service="dns"}[1h]))) * 100

# Top blocked
topk(20, sum by (query_name) (count_over_time({service="pihole", status="blocked"}[24h])))
```

## Auto-Provisioning Configuration

**Datasource** (`datasources/loki.yml`):
- Automatic Loki connection to `http://loki:3100`
- Set as default datasource
- 1000 max lines per query

**Dashboard Provider** (`dashboards/dashboards.yml`):
- Auto-loads all JSON files from provisioning directory
- Creates "Orion Sentinel" folder in Grafana
- Updates every 10 seconds
- Allows UI edits

## Color Schemes

**Health Score Gauge:**
- Red: 0-69 (F-D grades)
- Yellow: 70-89 (C-B grades)
- Green: 90-100 (A grade)

**Threat Counters:**
- Green: 0 (no threats)
- Yellow: 1-4 (low threat)
- Red: 5+ (significant threats)

**Block Rate:**
- Green: < 50%
- Yellow: 50-79%
- Red: ≥ 80%

## Performance Optimizations

- 30-second refresh interval (balance between freshness and load)
- Limited to 1000 log lines per query
- Aggregated metrics instead of raw logs where possible
- Efficient LogQL queries with proper time ranges
- Suitable for Raspberry Pi 5 deployment

## DNS Repository Integration

For integration with `orion-sentinel-dns-ha`:

1. **Pi-hole logs**: Forward to Loki with label `service="pihole"`
2. **DNS query logs**: Use label `service="dns"`
3. **Expected fields**:
   - `query_name`: Domain being queried
   - `client_ip`: Requesting device IP
   - `status`: "allowed" or "blocked"

Example Promtail config for DNS logs:
```yaml
scrape_configs:
  - job_name: pihole
    static_configs:
      - targets:
          - localhost
        labels:
          service: pihole
          __path__: /var/log/pihole/*.log
```

## Access Instructions

1. Start stack: `cd stacks/ai && docker-compose up -d`
2. Access Grafana: http://localhost:3000
3. Login: admin / admin (change on first login)
4. Navigate to "Dashboards" → "Orion Sentinel" folder
5. Select "SOC Management Dashboard" or "DNS & Pi-hole Dashboard"

## Customization

All dashboards are editable through Grafana UI:
- Click panel title → Edit
- Modify queries, thresholds, visualizations
- Changes persist in Grafana database
- Export updated JSON if needed for version control

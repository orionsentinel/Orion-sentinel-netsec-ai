# Logging and Dashboards

This document explains how to use Loki for log storage and Grafana for visualization in the Orion Sentinel NSM + AI system.

## Loki Overview

Loki is a horizontally-scalable, highly-available log aggregation system inspired by Prometheus. Unlike traditional log systems, Loki:
- **Indexes only metadata** (labels), not log content
- **Stores logs compressed** for efficiency
- **Queries logs in real-time** using LogQL

### Architecture

```
Log Sources → Promtail → Loki → Grafana
                          ↓
                     Local Storage
```

## Log Sources and Labels

### Label Schema

All logs in Loki use these labels:

| Label       | Values                                              | Purpose                          |
|-------------|-----------------------------------------------------|----------------------------------|
| `service`   | suricata, pihole, unbound, ai-device, ai-domain     | Identify log source              |
| `pi`        | pi1-dns, pi2-security                               | Identify which Pi generated log  |
| `log_type`  | nsm, dns, ai                                        | High-level log category          |
| `severity`  | info, warning, critical (AI logs only)              | Alert level for AI events        |
| `event_type`| alert, flow, dns, http, tls (Suricata logs only)    | Suricata event type              |

### Log Format

All logs are stored as JSON for structured querying.

#### Suricata Logs (eve.json)

Example alert:
```json
{
  "timestamp": "2024-01-15T10:30:00.123456+0000",
  "flow_id": 1234567890,
  "event_type": "alert",
  "src_ip": "192.168.1.50",
  "src_port": 52341,
  "dest_ip": "1.2.3.4",
  "dest_port": 443,
  "proto": "TCP",
  "alert": {
    "action": "allowed",
    "gid": 1,
    "signature_id": 2024001,
    "rev": 1,
    "signature": "ET MALWARE Possible C2 Communication",
    "category": "A Network Trojan was detected",
    "severity": 1
  }
}
```

Example DNS:
```json
{
  "timestamp": "2024-01-15T10:30:00.123456+0000",
  "event_type": "dns",
  "src_ip": "192.168.1.50",
  "src_port": 54321,
  "dest_ip": "192.168.1.10",
  "dest_port": 53,
  "proto": "UDP",
  "dns": {
    "type": "query",
    "id": 12345,
    "rrname": "example.com",
    "rrtype": "A",
    "tx_id": 0
  }
}
```

#### Pi-hole Logs

Example query log:
```
Jan 15 10:30:00 dnsmasq[1234]: query[A] example.com from 192.168.1.50
Jan 15 10:30:01 dnsmasq[1234]: forwarded example.com to 1.1.1.1
Jan 15 10:30:02 dnsmasq[1234]: reply example.com is 93.184.216.34
```

#### AI Service Logs

Device anomaly result:
```json
{
  "timestamp": "2024-01-15T10:35:00.000000+0000",
  "service": "ai-device-anomaly",
  "severity": "warning",
  "device_ip": "192.168.1.50",
  "window_start": "2024-01-15T10:25:00",
  "window_end": "2024-01-15T10:35:00",
  "anomaly_score": 0.87,
  "features": {
    "connection_count": 1523,
    "bytes_sent": 4523000,
    "bytes_received": 52341000,
    "unique_destinations": 45,
    "dns_query_count": 234,
    "unique_domains": 67
  }
}
```

Domain risk result:
```json
{
  "timestamp": "2024-01-15T10:35:00.000000+0000",
  "service": "ai-domain-risk",
  "severity": "critical",
  "domain": "xn--c1yn36f.xyz",
  "risk_score": 0.92,
  "action": "BLOCK",
  "features": {
    "domain_length": 14,
    "entropy": 3.2,
    "tld": "xyz",
    "subdomain_count": 0
  },
  "reason": "High entropy, rare TLD, DGA-like pattern"
}
```

---

## LogQL Query Language

LogQL is Loki's query language, similar to PromQL (Prometheus).

### Basic Query Structure

```
{<label_selector>} |= "<string_filter>" | <parser> | <filter_expression>
```

### Log Stream Selector (Labels)

Select logs by labels:

```logql
# All Suricata logs
{service="suricata"}

# All DNS logs (from any source)
{log_type="dns"}

# Pi-hole logs only
{service="pihole", pi="pi1-dns"}

# AI alerts with high severity
{service=~"ai-.*", severity="critical"}
```

### Line Filters

Filter log lines by content:

```logql
# Suricata alerts only
{service="suricata"} |= "alert"

# DNS queries for specific domain
{service="pihole"} |= "example.com"

# Exclude healthcheck traffic
{service="suricata"} != "healthcheck"
```

### Parsing JSON

Extract fields from JSON logs:

```logql
# Parse Suricata JSON and filter by source IP
{service="suricata"} 
  | json 
  | src_ip = "192.168.1.50"

# Parse and filter DNS queries
{service="suricata", event_type="dns"} 
  | json 
  | dns_type = "query"
  | dns_rrname =~ ".*malware.*"
```

### Aggregations

Count, rate, and aggregate logs:

```logql
# Count Suricata alerts per minute
rate({service="suricata", event_type="alert"}[1m])

# Total bytes from Suricata flows
sum by (src_ip) (
  sum_over_time({service="suricata", event_type="flow"} | json | unwrap bytes [5m])
)

# Top 10 queried domains
topk(10,
  sum by (rrname) (
    count_over_time({service="suricata", event_type="dns"} | json [1h])
  )
)
```

---

## Useful Queries

### Network Security Monitoring

**Top Talkers (by connection count)**:
```logql
topk(10,
  sum by (src_ip) (
    count_over_time({service="suricata", event_type="flow"}[1h])
  )
)
```

**Top Talkers (by bytes)**:
```logql
topk(10,
  sum by (src_ip) (
    sum_over_time({service="suricata", event_type="flow"} | json | unwrap bytes [1h])
  )
)
```

**Alert Rate Over Time**:
```logql
rate({service="suricata", event_type="alert"}[5m])
```

**Top Alert Signatures**:
```logql
topk(10,
  count_over_time({service="suricata", event_type="alert"} | json | unwrap signature [24h])
)
```

**TLS Connections by SNI**:
```logql
{service="suricata", event_type="tls"} 
  | json 
  | tls_sni != ""
```

### DNS Analytics

**Top Queried Domains**:
```logql
topk(20,
  sum by (rrname) (
    count_over_time({service="suricata", event_type="dns"} | json | dns_type="query" [1h])
  )
)
```

**DNS Query Rate**:
```logql
rate({service="pihole"}[5m])
```

**Blocked Queries (from Pi-hole)**:
```logql
{service="pihole"} |= "blocked"
```

**Queries for Rare TLDs**:
```logql
{service="suricata", event_type="dns"} 
  | json 
  | dns_rrname =~ ".*\\.(xyz|top|tk|ml)$"
```

### AI Detection

**Device Anomalies (high score)**:
```logql
{service="ai-device-anomaly"} 
  | json 
  | anomaly_score > 0.7
```

**High-Risk Domains Detected**:
```logql
{service="ai-domain-risk", severity="critical"}
```

**Blocked Domains (enforcement actions)**:
```logql
{service="ai-domain-risk"} 
  | json 
  | action = "BLOCK"
```

**Anomaly Score Trend**:
```logql
avg_over_time(
  {service="ai-device-anomaly"} | json | unwrap anomaly_score [1h]
)
```

---

## Grafana Dashboard Setup

### Creating a Dashboard

1. **Login to Grafana**: `http://pi2-ip:3000`
2. Left menu → Dashboards → New Dashboard
3. Add Panel
4. Configure panel:
   - Select "Loki" datasource
   - Enter LogQL query
   - Choose visualization (Time series, Table, Stat, etc.)

### Example Dashboard Layouts

#### Dashboard 1: Network Overview

**Panels**:
1. **Total Connections (Last Hour)** - Stat
   ```logql
   count_over_time({service="suricata", event_type="flow"}[1h])
   ```

2. **Connection Rate** - Time Series
   ```logql
   rate({service="suricata", event_type="flow"}[5m])
   ```

3. **Top Source IPs** - Table
   ```logql
   topk(10, sum by (src_ip) (count_over_time({service="suricata", event_type="flow"}[1h])))
   ```

4. **Protocol Distribution** - Pie Chart
   ```logql
   sum by (proto) (count_over_time({service="suricata", event_type="flow"}[1h]))
   ```

#### Dashboard 2: Security Alerts

**Panels**:
1. **Alert Count (Last 24h)** - Stat
   ```logql
   count_over_time({service="suricata", event_type="alert"}[24h])
   ```

2. **Alert Timeline** - Time Series
   ```logql
   rate({service="suricata", event_type="alert"}[5m])
   ```

3. **Top Alert Signatures** - Bar Gauge
   ```logql
   topk(10, count_over_time({service="suricata", event_type="alert"} | json | unwrap signature [24h]))
   ```

4. **Recent Alerts** - Logs Panel
   ```logql
   {service="suricata", event_type="alert"} | json
   ```
   Display fields: `timestamp`, `src_ip`, `dest_ip`, `alert.signature`

#### Dashboard 3: DNS Analytics

**Panels**:
1. **DNS Query Rate** - Time Series
   ```logql
   rate({service="pihole"}[5m])
   ```

2. **Top Queried Domains** - Table
   ```logql
   topk(20, sum by (rrname) (count_over_time({service="suricata", event_type="dns"} | json [1h])))
   ```

3. **Blocked Queries** - Time Series
   ```logql
   rate({service="pihole"} |= "blocked" [5m])
   ```

4. **Query Type Distribution** - Pie Chart
   ```logql
   sum by (rrtype) (count_over_time({service="suricata", event_type="dns"} | json [1h]))
   ```

#### Dashboard 4: AI Detection

**Panels**:
1. **Anomaly Score Distribution** - Histogram
   ```logql
   {service="ai-device-anomaly"} | json | unwrap anomaly_score
   ```

2. **High-Risk Devices** - Table
   ```logql
   {service="ai-device-anomaly"} | json | anomaly_score > 0.7
   ```
   Display: `device_ip`, `anomaly_score`, `connection_count`, `unique_domains`

3. **Blocked Domains** - Logs Panel
   ```logql
   {service="ai-domain-risk"} | json | action = "BLOCK"
   ```
   Display: `timestamp`, `domain`, `risk_score`, `reason`

4. **Enforcement Actions Over Time** - Time Series
   ```logql
   rate({service="ai-domain-risk"} | json | action = "BLOCK" [5m])
   ```

---

## Query Performance Tips

### Use Labels, Not Line Filters

**Good** (uses indexed labels):
```logql
{service="suricata", event_type="alert"}
```

**Bad** (scans all Suricata logs):
```logql
{service="suricata"} |= "alert"
```

### Limit Time Range

Shorter time ranges = faster queries:
- Use variables: `$__interval` for auto-adjusting
- Default to 1h or 6h, not 7d

### Use Appropriate Aggregations

For large time ranges, use `rate()` or `count_over_time()` instead of raw logs.

### Filter Early

Apply filters as early as possible in the query:
```logql
{service="suricata", event_type="dns"} | json | src_ip="192.168.1.50"
```

---

## Alerting

Grafana can send alerts based on LogQL queries.

### Example: Alert on High Anomaly Score

1. Create panel with query:
   ```logql
   max_over_time({service="ai-device-anomaly"} | json | unwrap anomaly_score [5m])
   ```

2. Add Alert Rule:
   - Condition: `max() > 0.9`
   - Evaluate every: 1m
   - For: 5m (wait 5 minutes before firing)

3. Configure Notification Channel:
   - Email, Slack, Discord, etc.
   - Add channel in Grafana → Alerting → Contact Points

### Example: Alert on Critical AI Events

Query:
```logql
count_over_time({service="ai-domain-risk", severity="critical"}[5m]) > 0
```

Alert when any critical domain is detected in 5-minute window.

---

## Loki Configuration

### Retention Policy

Edit `stacks/nsm/loki/loki-config.yaml`:

```yaml
limits_config:
  retention_period: 168h  # 7 days
```

Adjust based on disk space. For Pi #2 with 64 GB storage:
- 7 days: ~20-30 GB (moderate traffic)
- 14 days: ~40-60 GB (moderate traffic)

### Compaction

Loki automatically compacts chunks to save space. No manual intervention needed.

### Query Limits

To prevent queries from overwhelming the Pi:

```yaml
limits_config:
  max_query_length: 721h  # 30 days max
  max_query_lookback: 0   # No limit
  max_entries_limit_per_query: 5000
  max_streams_per_user: 0  # No limit
```

---

## Backup and Restore

### Backup Loki Data

```bash
# Stop Loki
cd ~/orion-sentinel-nsm-ai/stacks/nsm
docker compose stop loki

# Backup data directory
sudo tar -czf loki-backup-$(date +%Y%m%d).tar.gz loki/data/

# Restart Loki
docker compose start loki
```

### Restore Loki Data

```bash
# Stop Loki
docker compose stop loki

# Remove old data
sudo rm -rf loki/data/*

# Extract backup
sudo tar -xzf loki-backup-20240115.tar.gz

# Restart Loki
docker compose start loki
```

### Export Dashboards

In Grafana:
1. Open dashboard
2. Settings (gear icon) → JSON Model
3. Copy JSON
4. Save to file: `dashboard-network-overview.json`

To import:
1. Dashboards → Import
2. Paste JSON or upload file

---

## Troubleshooting

### Loki Returns No Data

**Check**:
1. Logs are being written: `docker compose logs promtail`
2. Loki is receiving data: `curl "http://localhost:3100/loki/api/v1/label/service/values"`
3. Query syntax is correct
4. Time range includes data

### Queries are Slow

**Solutions**:
1. Reduce time range
2. Use more specific label selectors
3. Avoid `|=` line filters when possible
4. Increase Loki resources in docker-compose.yml

### Grafana Can't Connect to Loki

**Check**:
1. Loki is running: `docker compose ps loki`
2. Loki health: `curl http://localhost:3100/ready`
3. Datasource URL is correct: `http://loki:3100` (internal Docker network)

**Fix**:
```bash
docker compose restart loki grafana
```

### Promtail Not Shipping Logs

**Check**:
1. Promtail is running: `docker compose ps promtail`
2. Promtail config is correct: `cat promtail/promtail-config.yml`
3. Log files exist and are readable
4. Loki endpoint is reachable from Promtail container

**Debug**:
```bash
docker compose logs promtail
```

---

## Further Reading

- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [LogQL Reference](https://grafana.com/docs/loki/latest/logql/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/dashboards/)

---

**See Also**:
- [architecture.md](architecture.md) for system design
- [pi2-setup.md](pi2-setup.md) for setup instructions

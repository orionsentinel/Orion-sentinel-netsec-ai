# Grafana Dashboards for NetSec Pi

This document describes the Grafana dashboards to be configured on **CoreSrv** for monitoring the NetSec Pi network security sensor.

All dashboards are designed to run on CoreSrv's Grafana instance, querying:
- **Loki** for logs from NetSec Pi (Suricata events, system logs)
- **Prometheus** for metrics from NetSec Pi (node exporter, optional Suricata metrics)

---

## Dashboard Overview

| Dashboard Name | Purpose | Data Sources | Refresh Rate |
|----------------|---------|--------------|--------------|
| **NetSec Pi - Overview** | High-level health and key metrics | Loki + Prometheus | 30s |
| **Suricata Alerts** | Detailed alert analysis | Loki | 30s |
| **Network Traffic Analysis** | Top talkers, destinations, protocols | Loki | 1m |
| **NetSec Node Health** | System resources (CPU, RAM, disk, network) | Prometheus | 30s |
| **DNS Analysis** (optional) | DNS queries from Suricata DNS logs | Loki | 1m |

---

## Dashboard 1: NetSec Pi - Overview

**Purpose:** Single-pane view of NetSec sensor health and recent activity

### Panels

#### Row 1: Key Metrics (Single Stat Panels)

**Panel: Total Alerts (Last 24h)**
- **Query Type:** Loki
- **Query:**
  ```logql
  count_over_time({orion_node_role="netsec", app="suricata"} | json | event_type="alert" [24h])
  ```
- **Visualization:** Stat panel
- **Thresholds:** 
  - Green: < 50
  - Yellow: 50-200
  - Red: > 200

**Panel: High-Severity Alerts (Last 24h)**
- **Query Type:** Loki
- **Query:**
  ```logql
  count_over_time({orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="alert" 
    | alert_severity <= 2 [24h])
  ```
- **Visualization:** Stat panel
- **Thresholds:**
  - Green: 0
  - Yellow: 1-5
  - Red: > 5

**Panel: NetSec Pi CPU Usage**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle", orion_node_role="netsec"}[5m])) * 100)
  ```
- **Visualization:** Gauge
- **Unit:** Percent (0-100)
- **Thresholds:**
  - Green: < 70%
  - Yellow: 70-90%
  - Red: > 90%

**Panel: NVMe Disk Usage**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  (node_filesystem_size_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"} 
   - node_filesystem_free_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"}) 
  / node_filesystem_size_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"} * 100
  ```
- **Visualization:** Gauge
- **Unit:** Percent (0-100)
- **Thresholds:**
  - Green: < 80%
  - Yellow: 80-95%
  - Red: > 95%

#### Row 2: Time Series Graphs

**Panel: Alerts Over Time (Last 24h)**
- **Query Type:** Loki
- **Query:**
  ```logql
  sum(count_over_time({orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="alert" [5m])) by (alert_severity)
  ```
- **Visualization:** Time series (stacked area)
- **Legend:** Alert severity (1 = high, 2 = medium, 3 = low)
- **Y-Axis:** Events per 5 minutes

**Panel: Network Traffic Rate**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  rate(node_network_receive_bytes_total{orion_node_role="netsec", device="eth0"}[5m])
  ```
- **Visualization:** Time series (line graph)
- **Unit:** Bytes/sec
- **Legend:** RX (receive), TX (transmit)

#### Row 3: Recent Events Table

**Panel: Latest High-Severity Alerts**
- **Query Type:** Loki
- **Query:**
  ```logql
  {orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="alert" 
    | alert_severity <= 2
  ```
- **Visualization:** Table
- **Columns:** 
  - Timestamp
  - Signature (alert.signature)
  - Source IP (src_ip)
  - Dest IP (dest_ip)
  - Severity (alert.severity)
  - Category (alert.category)
- **Limit:** 20 most recent

---

## Dashboard 2: Suricata Alerts

**Purpose:** Detailed analysis of Suricata IDS alerts

### Panels

#### Row 1: Alert Breakdown

**Panel: Alerts by Severity (Pie Chart)**
- **Query Type:** Loki
- **Query:**
  ```logql
  sum by (alert_severity) (
    count_over_time({orion_node_role="netsec", app="suricata"} 
      | json 
      | event_type="alert" [24h])
  )
  ```
- **Visualization:** Pie chart
- **Legend:** Severity 1 (Critical), 2 (High), 3 (Medium)

**Panel: Alerts by Category (Bar Chart)**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(10, 
    sum by (alert_category) (
      count_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="alert" [24h])
    )
  )
  ```
- **Visualization:** Bar chart (horizontal)
- **Limit:** Top 10 categories

#### Row 2: Alert Sources and Destinations

**Panel: Top Source IPs Generating Alerts**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(10, 
    sum by (src_ip) (
      count_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="alert" [24h])
    )
  )
  ```
- **Visualization:** Table
- **Columns:** Source IP, Alert Count
- **Limit:** Top 10

**Panel: Top Destination IPs in Alerts**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(10, 
    sum by (dest_ip) (
      count_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="alert" [24h])
    )
  )
  ```
- **Visualization:** Table
- **Columns:** Destination IP, Alert Count
- **Limit:** Top 10

#### Row 3: Alert Signatures

**Panel: Most Common Alert Signatures**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(15, 
    sum by (alert_signature) (
      count_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="alert" [24h])
    )
  )
  ```
- **Visualization:** Table
- **Columns:** Signature, Count
- **Limit:** Top 15

#### Row 4: Alert Timeline

**Panel: Alert Rate Over Time (Heatmap)**
- **Query Type:** Loki
- **Query:**
  ```logql
  sum by (alert_signature) (
    count_over_time({orion_node_role="netsec", app="suricata"} 
      | json 
      | event_type="alert" [5m])
  )
  ```
- **Visualization:** Heatmap
- **X-Axis:** Time
- **Y-Axis:** Alert signature
- **Color:** Count (blue = low, red = high)

---

## Dashboard 3: Network Traffic Analysis

**Purpose:** Analyze network flows, top talkers, and protocol distribution

### Panels

#### Row 1: Traffic Overview

**Panel: Total Bytes Transferred (Last 24h)**
- **Query Type:** Loki
- **Query:**
  ```logql
  sum(sum_over_time({orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="flow" 
    | unwrap flow_bytes_toserver [24h]))
  + 
  sum(sum_over_time({orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="flow" 
    | unwrap flow_bytes_toclient [24h]))
  ```
- **Visualization:** Stat panel
- **Unit:** Bytes (auto-format to GB/TB)

**Panel: Total Connections (Last 24h)**
- **Query Type:** Loki
- **Query:**
  ```logql
  count_over_time({orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="flow" [24h])
  ```
- **Visualization:** Stat panel

#### Row 2: Top Talkers

**Panel: Top Source IPs by Bytes Sent**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(10, 
    sum by (src_ip) (
      sum_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="flow" 
        | unwrap flow_bytes_toserver [24h])
    )
  )
  ```
- **Visualization:** Table
- **Columns:** Source IP, Bytes Sent
- **Limit:** Top 10

**Panel: Top Destination IPs by Bytes Received**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(10, 
    sum by (dest_ip) (
      sum_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="flow" 
        | unwrap flow_bytes_toclient [24h])
    )
  )
  ```
- **Visualization:** Table
- **Columns:** Destination IP, Bytes Received
- **Limit:** Top 10

#### Row 3: Protocol Distribution

**Panel: Protocols by Connection Count**
- **Query Type:** Loki
- **Query:**
  ```logql
  sum by (proto) (
    count_over_time({orion_node_role="netsec", app="suricata"} 
      | json 
      | event_type="flow" [24h])
  )
  ```
- **Visualization:** Pie chart
- **Legend:** TCP, UDP, ICMP, etc.

**Panel: Top Application Protocols**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(10, 
    sum by (app_proto) (
      count_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="flow" 
        | app_proto != "" [24h])
    )
  )
  ```
- **Visualization:** Bar chart
- **Legend:** HTTP, TLS, DNS, SSH, etc.

---

## Dashboard 4: NetSec Node Health

**Purpose:** Monitor NetSec Pi system resources and health

### Panels

#### Row 1: CPU and Memory

**Panel: CPU Usage by Core**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  100 - (avg by (cpu) (irate(node_cpu_seconds_total{mode="idle", orion_node_role="netsec"}[5m])) * 100)
  ```
- **Visualization:** Time series (multi-line)
- **Legend:** CPU0, CPU1, CPU2, CPU3
- **Y-Axis:** Percent (0-100)

**Panel: Memory Usage**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  (node_memory_MemTotal_bytes{orion_node_role="netsec"} 
   - node_memory_MemAvailable_bytes{orion_node_role="netsec"}) 
  / node_memory_MemTotal_bytes{orion_node_role="netsec"} * 100
  ```
- **Visualization:** Gauge
- **Unit:** Percent (0-100)
- **Thresholds:**
  - Green: < 80%
  - Yellow: 80-95%
  - Red: > 95%

#### Row 2: Disk and Network

**Panel: NVMe Disk I/O**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  rate(node_disk_read_bytes_total{orion_node_role="netsec", device="nvme0n1"}[5m])
  ```
  ```promql
  rate(node_disk_written_bytes_total{orion_node_role="netsec", device="nvme0n1"}[5m])
  ```
- **Visualization:** Time series
- **Legend:** Read, Write
- **Unit:** Bytes/sec

**Panel: Network I/O (eth0)**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  rate(node_network_receive_bytes_total{orion_node_role="netsec", device="eth0"}[5m])
  ```
  ```promql
  rate(node_network_transmit_bytes_total{orion_node_role="netsec", device="eth0"}[5m])
  ```
- **Visualization:** Time series
- **Legend:** RX, TX
- **Unit:** Bytes/sec

#### Row 3: Disk Space

**Panel: NVMe Disk Usage (Breakdown)**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  node_filesystem_size_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"} 
  - node_filesystem_free_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"}
  ```
  ```promql
  node_filesystem_free_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"}
  ```
- **Visualization:** Stacked bar chart
- **Legend:** Used, Free
- **Unit:** Bytes (auto-format to GB)

**Panel: System Uptime**
- **Query Type:** Prometheus
- **Query:**
  ```promql
  node_time_seconds{orion_node_role="netsec"} 
  - node_boot_time_seconds{orion_node_role="netsec"}
  ```
- **Visualization:** Stat panel
- **Unit:** Seconds (display as "Xd Xh Xm")

#### Row 4: Container Health

**Panel: Docker Container Status**
- **Query Type:** Prometheus (requires cAdvisor or Docker metrics exporter)
- **Query:**
  ```promql
  container_last_seen{orion_node_role="netsec"}
  ```
- **Visualization:** Table
- **Columns:** Container name, Status, CPU %, Memory %

---

## Dashboard 5: DNS Analysis (Optional)

**Purpose:** Analyze DNS queries captured by Suricata

### Panels

#### Row 1: DNS Overview

**Panel: Total DNS Queries (Last 24h)**
- **Query Type:** Loki
- **Query:**
  ```logql
  count_over_time({orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="dns" 
    | dns_type="query" [24h])
  ```
- **Visualization:** Stat panel

**Panel: DNS Queries per Minute**
- **Query Type:** Loki
- **Query:**
  ```logql
  sum(count_over_time({orion_node_role="netsec", app="suricata"} 
    | json 
    | event_type="dns" 
    | dns_type="query" [1m]))
  ```
- **Visualization:** Time series
- **Y-Axis:** Queries/min

#### Row 2: Top Domains

**Panel: Most Queried Domains**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(20, 
    sum by (dns_rrname) (
      count_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="dns" 
        | dns_type="query" [24h])
    )
  )
  ```
- **Visualization:** Table
- **Columns:** Domain (dns.rrname), Query Count
- **Limit:** Top 20

**Panel: Top Clients by DNS Queries**
- **Query Type:** Loki
- **Query:**
  ```logql
  topk(10, 
    sum by (src_ip) (
      count_over_time({orion_node_role="netsec", app="suricata"} 
        | json 
        | event_type="dns" 
        | dns_type="query" [24h])
    )
  )
  ```
- **Visualization:** Table
- **Columns:** Client IP, Query Count
- **Limit:** Top 10

#### Row 3: DNS Record Types

**Panel: DNS Query Types Distribution**
- **Query Type:** Loki
- **Query:**
  ```logql
  sum by (dns_rrtype) (
    count_over_time({orion_node_role="netsec", app="suricata"} 
      | json 
      | event_type="dns" 
      | dns_type="query" [24h])
  )
  ```
- **Visualization:** Pie chart
- **Legend:** A, AAAA, PTR, MX, TXT, etc.

---

## Prometheus Scrape Configuration

Add this to CoreSrv's `prometheus.yml` to scrape NetSec Pi metrics:

```yaml
scrape_configs:
  # NetSec Pi - Node Exporter
  - job_name: 'netsec-node-exporter'
    static_configs:
      - targets: ['192.168.x.x:9100']  # Replace with NetSec Pi IP
        labels:
          orion_node_role: 'netsec'
          orion_node_name: 'netsec-pi-01'
          instance: 'netsec-pi-01'

  # Optional: Suricata metrics exporter (if configured)
  # - job_name: 'netsec-suricata-metrics'
  #   static_configs:
  #     - targets: ['192.168.x.x:9200']
  #       labels:
  #         orion_node_role: 'netsec'
  #         app: 'suricata'
```

---

## Loki Datasource Configuration

Add this to CoreSrv's Grafana datasources:

```yaml
apiVersion: 1

datasources:
  - name: Loki-Orion
    type: loki
    access: proxy
    url: http://loki:3100
    jsonData:
      maxLines: 1000
      derivedFields:
        # Link to Suricata rule details (if available)
        - name: Signature ID
          matcherRegex: '"signature_id":(\d+)'
          url: 'https://rules.emergingthreats.net/open/suricata-6.0/rules/?signature=$1'
```

---

## Dashboard JSON Export

### Example: NetSec Pi Overview Dashboard JSON Structure

```json
{
  "dashboard": {
    "title": "NetSec Pi - Overview",
    "tags": ["orion", "netsec", "security"],
    "timezone": "browser",
    "refresh": "30s",
    "panels": [
      {
        "id": 1,
        "title": "Total Alerts (Last 24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "count_over_time({orion_node_role=\"netsec\", app=\"suricata\"} | json | event_type=\"alert\" [24h])",
            "refId": "A",
            "datasource": "Loki-Orion"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                { "value": 0, "color": "green" },
                { "value": 50, "color": "yellow" },
                { "value": 200, "color": "red" }
              ]
            }
          }
        }
      }
      // ... more panels
    ]
  }
}
```

To export full dashboard JSON:
1. Create dashboard in Grafana UI
2. Click "Share" → "Export" → "Save to file"
3. Commit JSON to `grafana_dashboards/` directory in this repo

---

## Dashboard Provisioning

To auto-provision dashboards on CoreSrv Grafana:

**Create:** `coresrv-grafana/provisioning/dashboards/netsec.yml`

```yaml
apiVersion: 1

providers:
  - name: 'Orion NetSec Dashboards'
    orgId: 1
    folder: 'Orion Sentinel'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/netsec
```

**Place dashboard JSON files in:** `coresrv-grafana/provisioning/dashboards/netsec/`

Example:
- `netsec-overview.json`
- `suricata-alerts.json`
- `network-traffic.json`
- `node-health.json`

---

## Alert Rules (Prometheus Alertmanager)

Example alert rules to add to CoreSrv Prometheus:

```yaml
groups:
  - name: netsec_alerts
    interval: 1m
    rules:
      # High-severity Suricata alerts
      - alert: NetSecHighSeverityAlerts
        expr: |
          sum(increase({orion_node_role="netsec", app="suricata"} 
            | json 
            | event_type="alert" 
            | alert_severity <= 2 [5m])) > 5
        for: 5m
        labels:
          severity: warning
          component: netsec
        annotations:
          summary: "High-severity Suricata alerts detected"
          description: "{{ $value }} high-severity alerts in last 5 minutes on {{ $labels.orion_node_name }}"

      # NetSec Pi high CPU usage
      - alert: NetSecHighCPU
        expr: |
          100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle", orion_node_role="netsec"}[5m])) * 100) > 90
        for: 10m
        labels:
          severity: warning
          component: netsec
        annotations:
          summary: "NetSec Pi high CPU usage"
          description: "CPU usage is {{ $value }}% on {{ $labels.instance }}"

      # NVMe disk almost full
      - alert: NetSecDiskAlmostFull
        expr: |
          (node_filesystem_size_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"} 
           - node_filesystem_free_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"}) 
          / node_filesystem_size_bytes{orion_node_role="netsec", mountpoint="/mnt/orion-nvme-netsec"} * 100 > 90
        for: 5m
        labels:
          severity: critical
          component: netsec
        annotations:
          summary: "NetSec NVMe disk almost full"
          description: "NVMe disk usage is {{ $value }}% on {{ $labels.instance }}"

      # Promtail not shipping logs
      - alert: NetSecPromtailDown
        expr: |
          up{job="netsec-promtail"} == 0
        for: 5m
        labels:
          severity: critical
          component: netsec
        annotations:
          summary: "NetSec Promtail is down"
          description: "Promtail on {{ $labels.instance }} has been down for 5 minutes"
```

---

## Summary

These dashboards provide comprehensive visibility into:
- **Security posture** (Suricata alerts, anomalies)
- **Network behavior** (top talkers, protocols, flows)
- **System health** (CPU, RAM, disk, network I/O)
- **DNS activity** (query rates, top domains)

All dashboards run on CoreSrv, not on the NetSec Pi itself, maintaining the clean sensor/SPoG architecture.

For dashboard JSON exports and updates, see the `grafana_dashboards/` directory in this repository.

---

**Next Steps:**
1. Set up CoreSrv with Loki, Prometheus, Grafana
2. Configure Prometheus scrape config for NetSec Pi
3. Import/provision dashboards on CoreSrv Grafana
4. Set up Prometheus Alertmanager rules
5. Test dashboards with live NetSec Pi data

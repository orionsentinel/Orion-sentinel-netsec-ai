# CoreSrv Dashboards Export Guide

This document explains how to export NetSec Grafana dashboards for use on CoreSrv's central Grafana instance.

## Overview

In the Single Pane of Glass (SPoG) architecture:
- **CoreSrv** hosts the central Grafana instance with all dashboards
- **NetSec node** provides dashboards in this repository for export
- Dashboards are designed to work with the generic "Loki" datasource name

## Dashboard Compatibility

All dashboards in `grafana/dashboards/` are designed to be datasource-agnostic:

- Use datasource variable: `${DS_LOKI}` or generic "Loki" datasource name
- Filter on labels: `host="pi-netsec"` or `node="netsec"`
- Compatible with both local and CoreSrv Loki instances

## Export Dashboards to CoreSrv

### Method 1: Direct File Copy (Recommended)

If you have access to both repositories:

```bash
# From NetSec repository
NETSEC_REPO=/path/to/Orion-sentinel-netsec-ai
CORESRV_REPO=/path/to/Orion-Sentinel-CoreSrv

# Copy all NetSec dashboards to CoreSrv
cp "$NETSEC_REPO/grafana/dashboards/"*.json \
   "$CORESRV_REPO/monitoring/grafana/dashboards/orion/"

# Restart CoreSrv Grafana to pick up new dashboards
cd "$CORESRV_REPO"
docker compose -f monitoring/docker-compose.yml restart grafana
```

### Method 2: Export from Grafana UI

If you're running NetSec in standalone mode with local Grafana:

1. **Access local NetSec Grafana**:
   ```bash
   # Start NetSec in standalone mode
   ./scripts/netsecctl.sh up-standalone
   
   # Open http://localhost:3000
   ```

2. **Export each dashboard**:
   - Navigate to dashboard
   - Click "Share" icon (top right)
   - Click "Export" tab
   - Click "Save to file"
   - Download JSON file

3. **Import to CoreSrv Grafana**:
   - Access CoreSrv Grafana (https://grafana.local)
   - Click "+" → "Import"
   - Upload the JSON file
   - Select "Loki" as datasource
   - Click "Import"

### Method 3: Grafana API Export/Import

Automated export and import using Grafana API:

```bash
# Export from NetSec Grafana
NETSEC_GRAFANA="http://localhost:3000"
NETSEC_API_KEY="your-netsec-api-key"

# Get dashboard UIDs
curl -H "Authorization: Bearer $NETSEC_API_KEY" \
     "$NETSEC_GRAFANA/api/search?type=dash-db" | jq '.[].uid'

# Export specific dashboard
DASHBOARD_UID="abc123"
curl -H "Authorization: Bearer $NETSEC_API_KEY" \
     "$NETSEC_GRAFANA/api/dashboards/uid/$DASHBOARD_UID" | \
     jq '.dashboard' > dashboard.json

# Import to CoreSrv Grafana
CORESRV_GRAFANA="https://grafana.local"
CORESRV_API_KEY="your-coresrv-api-key"

curl -X POST -H "Authorization: Bearer $CORESRV_API_KEY" \
     -H "Content-Type: application/json" \
     -d @dashboard.json \
     "$CORESRV_GRAFANA/api/dashboards/db"
```

## Available Dashboards

This repository includes the following dashboards (check `grafana/dashboards/` for actual files):

### Security Dashboards
- **Suricata Overview** - IDS alerts, events, and statistics
- **Threat Detection** - AI-detected threats and risk scores
- **Device Inventory** - Network device tracking and anomalies

### AI Service Dashboards
- **SOAR Automation** - Playbook execution and automation metrics
- **Health Score** - Network security health score trends
- **Change Detection** - Baseline changes and anomalies

### Technical Dashboards
- **Log Analysis** - Log volume, patterns, and search
- **Performance Metrics** - AI service performance and resource usage

## Dashboard Configuration for CoreSrv

### Datasource Configuration

Dashboards use the generic "Loki" datasource. On CoreSrv, ensure:

1. **Loki datasource exists** in `monitoring/grafana/provisioning/datasources/datasources.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    isDefault: true
```

2. **Dashboard provisioning** in `monitoring/grafana/provisioning/dashboards/orion.yml`:

```yaml
apiVersion: 1
providers:
  - name: "Orion Sentinel Dashboards"
    folder: "Orion Sentinel"
    type: file
    disableDeletion: false
    options:
      path: /var/lib/grafana/dashboards/orion
```

### Label Filtering

NetSec dashboards filter logs using labels:

- `host="pi-netsec"` - Filter to NetSec node only
- `job="suricata"` - Suricata IDS logs
- `job="ai"` - AI service logs
- `service="soar"` - SOAR service logs

These labels are automatically added by Promtail on the NetSec node.

## Customizing Dashboards for Multi-Node

If you have multiple NetSec nodes, customize dashboards:

### Add Node Variable

Add a dashboard variable to select nodes:

1. Dashboard Settings → Variables → Add variable
2. Name: `node`
3. Type: `Query`
4. Query: `label_values(host)`
5. Save

### Update Panels

Modify panel queries to use the variable:

```logql
# Before (single node)
{host="pi-netsec", job="suricata"}

# After (multi-node)
{host=~"$node", job="suricata"}
```

## Dashboard Maintenance

### Keeping Dashboards in Sync

1. **Make changes in NetSec repo** (single source of truth)
2. **Export to CoreSrv** when updated
3. **Version control** both repositories

### Dashboard Naming Convention

Use consistent naming to identify NetSec dashboards:

- Prefix: "NetSec - " (e.g., "NetSec - Suricata Overview")
- Folder: "Orion Sentinel / NetSec"
- Tags: `netsec`, `security`, `ai`

## Testing Dashboards

Before exporting to CoreSrv, test dashboards:

1. **Start NetSec in standalone mode**:
   ```bash
   ./scripts/netsecctl.sh up-standalone
   ```

2. **Generate test data**:
   - Let Suricata run for a while
   - Trigger some AI detections
   - Run SOAR playbooks

3. **Verify dashboard panels**:
   - All panels load without errors
   - Data appears correctly
   - Filters work as expected

4. **Check queries**:
   - Use Grafana "Explore" to test LogQL queries
   - Ensure queries are efficient (< 5s execution)

## Troubleshooting

### Dashboards Show No Data on CoreSrv

**Cause**: NetSec logs not reaching CoreSrv Loki

**Fix**:
1. Verify LOKI_URL in NetSec `.env`
2. Check Promtail logs: `docker logs orion-promtail`
3. Test Loki connectivity: `curl http://coresrv-ip:3100/ready`

### Datasource Error on Import

**Cause**: Loki datasource name mismatch

**Fix**:
1. Check CoreSrv datasource name in Grafana → Configuration → Data Sources
2. Re-import dashboard and select correct datasource
3. Or edit JSON and update datasource UID

### Panels Show "No data" or "N/A"

**Cause**: Label filters don't match actual labels in Loki

**Fix**:
1. Use Grafana Explore on CoreSrv
2. Run: `{host=~".*"}` to see all hosts
3. Verify NetSec host label: `{host="pi-netsec"}`
4. Update dashboard queries if needed

### Dashboard Looks Different on CoreSrv

**Cause**: Grafana version mismatch

**Fix**:
1. Ensure CoreSrv and NetSec use same Grafana version
2. Update dashboards to use compatible features
3. Test on CoreSrv Grafana version before finalizing

## Best Practices

1. **Single Source of Truth**: Keep dashboard sources in NetSec repo
2. **Version Control**: Commit dashboard JSON to git
3. **Documentation**: Document queries and panel purposes
4. **Testing**: Test in standalone mode before exporting
5. **Labeling**: Use consistent labels for filtering
6. **Performance**: Optimize queries for large log volumes
7. **Alerts**: Configure alerts in CoreSrv Grafana, not in dashboard JSON

## Related Documentation

- [CoreSrv Integration](CORESRV-INTEGRATION.md) - Integration guide
- [Logging and Dashboards](logging-and-dashboards.md) - Loki and Grafana setup
- [Architecture](architecture.md) - System architecture overview

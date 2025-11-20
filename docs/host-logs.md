# Host Log Integration (EDR-lite)

## Overview

The host logs module provides normalized ingestion of endpoint/host logs from various sources, enabling EDR-lite capabilities.

## Supported Sources

### Wazuh

**Description**: Open-source security monitoring platform

**Event Format**:
```json
{
  "agent": {"name": "hostname"},
  "rule": {"description": "...", "level": 5},
  "data": {...},
  "timestamp": "..."
}
```

**Integration**:
- Deploy Wazuh agent on endpoints
- Configure Wazuh to forward JSON logs
- Use Promtail to ship logs to Loki with label `service="host-logs"`, `source="wazuh"`

### osquery

**Description**: SQL-powered endpoint visibility

**Event Format**:
```json
{
  "name": "query_name",
  "hostIdentifier": "hostname",
  "unixTime": 1234567890,
  "columns": {...},
  "action": "added"
}
```

**Integration**:
- Deploy osquery on endpoints
- Configure scheduled queries
- Use Promtail to ship results to Loki with label `service="host-logs"`, `source="osquery"`

### Syslog

**Description**: Traditional system logging

**Event Format**:
```json
{
  "hostname": "...",
  "timestamp": "...",
  "severity": 3,
  "message": "..."
}
```

**Integration**:
- Configure rsyslog/syslog-ng to forward to Loki
- Use Promtail with syslog input
- Label with `service="host-logs"`, `source="syslog"`

## Normalized Event Model

All sources are normalized to `HostEvent`:

```python
{
  "hostname": "workstation-01",
  "event_type": "process_started",  # Normalized type
  "timestamp": "2025-01-15T10:30:00Z",
  "details": {...},  # Source-specific details
  "severity": "medium",  # Normalized severity
  "source": "osquery",  # Original source
  "user": "john",
  "process": "python3",
  "pid": 12345
}
```

## Event Types

- `file_created`, `file_modified`, `file_deleted`
- `process_started`, `process_terminated`
- `network_connection`
- `login_success`, `login_failed`
- `privilege_escalation`
- `registry_change` (Windows)
- `package_installed`, `package_removed`
- `service_started`, `service_stopped`
- `generic`

## Severity Levels

- `low`: Informational events
- `medium`: Notable events
- `high`: Suspicious events
- `critical`: Security incidents

## Deployment Example

### Minimal Setup (Single Endpoint)

#### 1. Install Wazuh Agent

```bash
# On Ubuntu/Debian endpoint
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | apt-key add -
echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | tee /etc/apt/sources.list.d/wazuh.list
apt-get update
apt-get install wazuh-agent
```

#### 2. Configure Wazuh Agent

Edit `/var/ossec/etc/ossec.conf`:

```xml
<ossec_config>
  <client>
    <server>
      <address>WAZUH_MANAGER_IP</address>
    </server>
  </client>
  
  <localfile>
    <log_format>json</log_format>
    <location>/var/ossec/logs/alerts/alerts.json</location>
  </localfile>
</ossec_config>
```

#### 3. Forward Logs with Promtail

Create `/etc/promtail/promtail-host-logs.yml`:

```yaml
server:
  http_listen_port: 9081

positions:
  filename: /tmp/positions-host-logs.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: wazuh
    static_configs:
      - targets:
          - localhost
        labels:
          service: host-logs
          source: wazuh
          host: ${HOSTNAME}
          __path__: /var/ossec/logs/alerts/alerts.json
```

Run Promtail:

```bash
promtail -config.file=/etc/promtail/promtail-host-logs.yml
```

### Advanced Setup (Multiple Endpoints)

Use Wazuh manager + agents architecture:

1. **Wazuh Manager**: Collects from all agents
2. **Promtail**: Ships manager logs to Loki
3. **Orion Sentinel**: Analyzes normalized events

## Normalization

Use the normalizer to convert raw logs:

```python
from orion_ai.host_logs.normalizer import HostLogNormalizer

normalizer = HostLogNormalizer()

# Wazuh event
wazuh_event = {
  "agent": {"name": "workstation-01"},
  "rule": {"level": 7, "description": "Suspicious process"},
  "data": {...}
}

host_event = normalizer.normalize(wazuh_event, source="wazuh")
```

## Loki Labels

Host logs should use these labels:

- `service="host-logs"`
- `source="wazuh|osquery|syslog"`
- `host="hostname"`
- `severity="low|medium|high|critical"`

## Querying Host Logs

### Loki Queries

```logql
# All host logs
{service="host-logs"}

# Specific host
{service="host-logs", host="workstation-01"}

# High severity events
{service="host-logs"} | json | severity="high"

# Process events
{service="host-logs"} | json | event_type=~"process_.*"

# Failed logins
{service="host-logs"} | json | event_type="login_failed"
```

## Integration with Other Modules

### SOAR Playbooks

React to host events:

```yaml
- id: alert-privilege-escalation
  name: Alert on Privilege Escalation
  match_event_type: host_event  # TODO: Add to EventType enum
  conditions:
    - field: fields.event_type
      operator: ==
      value: privilege_escalation
  actions:
    - action_type: SEND_NOTIFICATION
      parameters:
        message: "Privilege escalation on {{fields.hostname}} by {{fields.user}}"
        severity: critical
```

### Device Correlation

Link host events to inventory:

```python
# Get host by hostname, lookup IP
# Cross-reference with inventory
# Enrich device profile with host events
```

### Threat Intelligence

Correlate host indicators:

- Process hashes
- File paths
- Command lines
- Network connections

## Grafana Dashboards

Recommended panels:

- **Event timeline**: All host events over time
- **Event types**: Breakdown by type (pie chart)
- **Top hosts**: Most active endpoints
- **Failed logins**: Failed login attempts
- **Process activity**: Process starts/stops
- **File changes**: File modifications
- **Severity distribution**: Events by severity

## Recommended Queries (osquery)

Monitor these on endpoints:

### Processes
```sql
SELECT pid, name, path, cmdline FROM processes;
```

### Network Connections
```sql
SELECT pid, remote_address, remote_port FROM process_open_sockets;
```

### Users
```sql
SELECT uid, username, description FROM users;
```

### Installed Packages
```sql
SELECT name, version, install_time FROM deb_packages;
```

## Best Practices

1. **Start with critical endpoints**: Workstations, servers
2. **Filter noise**: Use Wazuh rules to filter low-value events
3. **Set retention**: Host logs can be verbose, set appropriate retention
4. **Monitor agent health**: Ensure agents are reporting
5. **Test queries**: Validate osquery queries don't impact performance
6. **Correlate**: Link host events with network events for full picture

## Performance Considerations

- **Agent overhead**: osquery/Wazuh use CPU/memory
- **Log volume**: High-frequency queries generate lots of logs
- **Network bandwidth**: Shipping logs to Loki uses bandwidth
- **Storage**: Retain based on compliance needs

Recommended:

- osquery: Run queries every 5-15 minutes
- Wazuh: Use rule filtering
- Loki: 30-90 day retention for host logs

## Security Considerations

1. **Agent communication**: Use TLS for Wazuh agent<->manager
2. **Log integrity**: Ensure logs aren't tampered with
3. **Sensitive data**: Filter passwords/keys from logs
4. **Access control**: Restrict who can view host logs

## Future Enhancements

- [ ] EDR-specific detections (MITRE ATT&CK)
- [ ] Automated response via agents
- [ ] File integrity monitoring (FIM)
- [ ] Registry monitoring (Windows)
- [ ] Kernel module monitoring
- [ ] Container/Docker monitoring
- [ ] Cloud instance monitoring (AWS, Azure)
- [ ] Process behavior analysis

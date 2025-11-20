# Change Monitor: "What Changed?"

## Overview

The change monitor detects behavioral and configuration changes in the network over time by comparing baseline snapshots.

## Concept

Security teams need to answer: **"What changed?"**

- New devices appeared
- Device started using new ports
- Device contacted new domains
- Risk scores changed
- Tags were modified

## Architecture

1. **Baseline Builder** (`baseline.py`): Creates snapshots of network state
2. **Change Analyzer** (`analyzer.py`): Compares baselines and detects changes
3. **Change Monitor Service** (`service.py`): Periodic change detection

## Baseline Types

### Global Baseline

Captures entire network state:

- All device IPs
- All observed ports
- All observed domains
- Device counts

### Device Baseline

Captures single device state:

- Observed ports
- Contacted domains
- Traffic patterns
- Tags
- Risk score

## Change Types

Detected changes:

- `new_device`: New device appeared
- `device_disappeared`: Device not seen recently
- `new_port_for_device`: Device using new port
- `new_domain_for_device`: Device contacted new domain
- `new_destination_for_device`: New IP destination
- `tag_changed`: Device tags modified
- `risk_score_increased`: Risk score went up
- `traffic_pattern_changed`: Unusual traffic volume

## Baseline Frequency

Default: One baseline every 24 hours covering the previous 7 days.

This provides:

- Daily change detection
- Week-long historical context
- Reasonable data volume

## Change Events

Change events are emitted to Loki with:

```json
{
  "change_type": "new_port_for_device",
  "entity": "192.168.1.50",
  "entity_type": "device",
  "old_value": [80, 443],
  "new_value": [80, 443, 22],
  "details": {
    "new_port": 22
  },
  "risk_level": "medium"
}
```

## Risk Assessment

Changes are automatically assessed for risk:

- **Critical**: Multiple high-risk changes
- **High**: High-risk ports (22, 3389, etc.), significant risk score increase
- **Medium**: Service ports, new devices
- **Low**: Normal activity, domain changes

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CHANGE_MONITOR_INTERVAL_HOURS` | `24` | Baseline interval |
| `CHANGE_MONITOR_PERIOD_DAYS` | `7` | Days of history in baseline |
| `LOKI_URL` | `http://localhost:3100` | Loki instance URL |

## Running the Service

```bash
cd stacks/ai
docker-compose up change-monitor
```

## Storage

Baselines are stored in `/data/baselines/` as JSON files:

```
/data/baselines/
  baseline_2025_01_15_000000.json
  baseline_2025_01_16_000000.json
  ...
```

## Integration with SOAR

SOAR playbooks can react to changes:

```yaml
- id: alert-new-high-risk-port
  name: Alert on New High-Risk Ports
  match_event_type: change_event
  conditions:
    - field: fields.change_type
      operator: ==
      value: new_port_for_device
    - field: fields.risk_level
      operator: ==
      value: high
  actions:
    - action_type: SEND_NOTIFICATION
      parameters:
        message: "High-risk port {{fields.new_port}} detected on {{fields.entity}}"
        severity: high
```

## Grafana Dashboards

Recommended panels:

- Changes over time (by type)
- Changes by risk level
- Top changing devices
- New devices timeline
- Port changes heatmap

## Loki Queries

```logql
# All change events
{service="change_monitor", stream="change_event"}

# High-risk changes
{service="change_monitor"} | json | risk_level="high"

# Specific change type
{service="change_monitor"} | json | change_type="new_device"

# Changes for device
{service="change_monitor"} | json | entity="192.168.1.50"
```

## Use Cases

### Security Monitoring

- Detect unauthorized device additions
- Identify configuration drift
- Spot behavioral anomalies

### Compliance

- Track network changes for audit trails
- Document when changes occurred
- Attribute changes to events

### Troubleshooting

- "What changed before the issue started?"
- Correlate changes with incidents
- Understand environment evolution

## Best Practices

1. **Review high-risk changes daily**
2. **Investigate new devices promptly**
3. **Correlate changes with tickets/events**
4. **Maintain change log for compliance**
5. **Tune risk thresholds based on environment**

## Example Workflow

1. Change monitor runs daily at midnight
2. Builds baseline for last 7 days
3. Compares with previous day's baseline
4. Detects new SSH port (22) on IoT device
5. Emits high-risk change event
6. SOAR playbook sends alert
7. Security team investigates

## Future Enhancements

- [ ] Configurable baseline schedules
- [ ] Change approval workflow
- [ ] Automatic rollback capabilities
- [ ] ML-based anomaly detection on changes
- [ ] Change correlation with external events
- [ ] Per-device baseline sensitivity

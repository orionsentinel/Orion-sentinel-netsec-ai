# Security Health Score

## Overview

The health score module provides an at-a-glance view of your network's security posture by combining multiple security metrics into a single score from 0-100.

## Components

### Health Metrics

The health score is calculated from these metrics:

1. **Unknown Device Count**: Number of devices without tags or type classification
2. **High Anomaly Count**: Critical device anomaly events in last 24 hours
3. **Intel Matches Count**: Threat intelligence matches in last 7 days
4. **New Devices Count**: New devices discovered in last 7 days
5. **Critical Events Count**: Unresolved critical events in last 7 days
6. **Suricata Alerts Count**: (Future) Suricata alerts in recent period

### Health Score

The overall health score (0-100) is calculated using weighted penalties:

```
Starting Score: 100
Penalties Applied:
  - Unknown Devices:    15% weight
  - High Anomalies:     30% weight
  - Intel Matches:      35% weight (highest)
  - New Devices:        10% weight
  - Critical Events:    10% weight
```

Penalties scale based on thresholds:

- **Low**: 30% of max penalty
- **Moderate**: 60% of max penalty  
- **High**: 100% of max penalty

### Health Status

Score is mapped to status:

- **Good**: 80-100
- **Fair**: 60-79
- **Poor**: 40-59
- **Critical**: 0-39

### Insights

The health score includes actionable insights highlighting the main concerns:

```
"5 unknown/untagged devices"
"3 high-severity anomalies in last 24h - moderate concern"
"2 threat intelligence matches in last 7 days - high concern"
```

## Health Score Service

The health score service runs periodically (default: every 60 minutes):

1. Collects metrics from device inventory and Loki events
2. Calculates weighted health score
3. Generates insights based on metric values
4. Emits `security_health_update` event to Loki

### Configuration

```bash
# How often to calculate health score
HEALTH_SCORE_INTERVAL_MINUTES=60
```

## Dashboard Display

The health score is prominently displayed on the main dashboard:

```
┌─────────────────────────────┐
│ Security Health             │
│                             │
│  85    Good                 │
│                             │
│  Last updated: 2024-01-15   │
│                             │
│  Key Insights:              │
│  ⚠️ 2 unknown devices       │
│  ⚠️ 1 new device (7 days)   │
└─────────────────────────────┘
```

Color coding:
- **Green** (80+): Good security posture
- **Orange** (60-79): Some concerns, review insights
- **Red** (<60): Immediate attention needed

## Customization

### Adjusting Weights

Modify weights in `health_score/calculator.py`:

```python
WEIGHTS = {
    "unknown_devices": 0.15,    # Adjust importance
    "high_anomalies": 0.30,
    "intel_matches": 0.35,      # Most important by default
    "new_devices": 0.10,
    "critical_events": 0.10,
}
```

### Adjusting Thresholds

Modify penalty thresholds:

```python
THRESHOLDS = {
    "unknown_devices": {"low": 2, "high": 5},
    "high_anomalies": {"low": 3, "high": 10},
    "intel_matches": {"low": 1, "high": 5},
    # ...
}
```

## API Access

Health score data is available via:

```bash
# JSON API
GET /api/health

Response:
{
  "score": 85,
  "status": "Good",
  "timestamp": "2024-01-15T10:30:00",
  "metrics": {
    "unknown_device_count": 2,
    "high_anomaly_count": 0,
    "intel_matches_count": 0,
    "new_devices_count": 1,
    "critical_events_count": 0
  },
  "insights": [
    "2 unknown/untagged devices",
    "1 new devices in last 7 days"
  ]
}
```

## Improving Your Score

### Quick Wins

1. **Tag Unknown Devices** (+15 points potential)
   - Review `/devices` and classify unknown devices
   - Add appropriate tags: `trusted`, `iot`, `lab`, etc.

2. **Investigate Anomalies** (+30 points potential)
   - Review device anomaly events
   - Determine if legitimate or concerning
   - Tag or isolate problematic devices

3. **Address Threat Intel Matches** (+35 points potential)
   - **Critical**: Review devices that contacted known bad indicators
   - Determine cause (malware, misconfiguration, etc.)
   - Take action: clean, isolate, or block

4. **Review New Devices** (+10 points potential)
   - Check if new devices are expected
   - Classify and tag appropriately
   - Remove unauthorized devices

### Long-Term Improvements

1. **Establish Baselines**
   - Tag all known devices
   - Set device types
   - Assign owners

2. **Enable SOAR Playbooks**
   - Auto-tag devices with anomalies
   - Auto-alert on critical events
   - Auto-block high-risk domains

3. **Regular Reviews**
   - Weekly device inventory review
   - Monthly security event analysis
   - Quarterly threat intel feed updates

4. **Tune Thresholds**
   - Adjust anomaly detection thresholds
   - Customize domain risk scoring
   - Fine-tune health score weights for your environment

## Events

Health score updates are logged as events:

```
Event Type: security_health_update
Severity: INFO | WARNING | CRITICAL (based on score)
Metadata:
  - score: 85
  - status: "Good"
  - metrics: { ... }
  - insights: [ ... ]
```

These events can trigger SOAR playbooks:

```yaml
- id: alert-low-health
  name: "Alert on Low Health Score"
  match_event_type: "security_health_update"
  conditions:
    - field: "metadata.score"
      operator: "<"
      value: 60
  actions:
    - type: "SEND_NOTIFICATION"
      params:
        subject: "Security Health Score Low"
        severity: "WARNING"
```

## Metrics Collection

Metrics are collected from:

1. **Device Inventory**: SQLite database (`/var/lib/orion-ai/devices.db`)
2. **Loki Events**: LogQL queries on `stream="events"`

Queries are cached for performance - calculations take <1 second on typical home networks.

## Future Enhancements

- [ ] Historical health score tracking
- [ ] Health score trends and graphs
- [ ] Custom metric definitions
- [ ] Multi-environment support
- [ ] Export health reports
- [ ] Scheduled health reports via email

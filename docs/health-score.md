# Security Health Score

## Overview

The health score provides a single 0-100 metric representing the overall security posture of your network.

## Score Components

The score is calculated from four weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Inventory Health | 25% | Device classification and management |
| Threat Landscape | 35% | Active threats and alerts |
| Change Management | 20% | Behavioral changes and new devices |
| Hygiene Practices | 20% | Security best practices |

## Scoring Formula

### Overall Score

```
Score = (Inventory × 0.25) + (Threat × 0.35) + (Change × 0.20) + (Hygiene × 0.20)
```

### Inventory Score (0-100)

Starts at 100, penalties for:

- **Unknown devices**: -30 points (scaled by ratio)
- **Untagged devices**: -20 points (scaled by ratio)
- **High-risk devices**: -50 points (scaled by ratio)

### Threat Score (0-100)

Starts at 100, penalties for:

- **High-severity anomalies (24h)**: -5 each (max -40)
- **Intel matches (24h)**: -10 each (max -30)
- **Intel matches (7d)**: -2 each (max -20)
- **Suricata alerts (24h)**: -1 each (max -10)
- **Unresolved incidents**: -5 each (max -20)

### Change Score (0-100)

Starts at 100, penalties for:

- **New devices (7d)**: -5 each (max -30)
- **High-risk changes (24h)**: -10 each (max -70)

### Hygiene Score (0-100)

Based on manual flags:

- **Backups OK**: +40 points
- **Updates current**: +40 points
- **Firewall enabled**: +20 points

## Letter Grades

| Score | Grade |
|-------|-------|
| 90-100 | A |
| 80-89 | B |
| 70-79 | C |
| 60-69 | D |
| 0-59 | F |

## Input Metrics

### Automated Metrics

Collected automatically from:

- **Inventory database**: Device counts, classifications, risk scores
- **Loki**: Event counts (anomalies, alerts, intel matches)
- **Change monitor**: New devices, changes

### Manual Metrics

Set via configuration file (`/config/hygiene.yml`):

```yaml
hygiene:
  backups_ok: true
  updates_current: true
  firewall_enabled: true
```

## Recommendations

The health score service generates actionable recommendations based on metrics:

- "Tag 5 unknown devices"
- "Investigate 2 high-severity anomalies"
- "Review 3 recent threat intel matches"
- "Set up or verify backup system"

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTH_SCORE_INTERVAL_HOURS` | `1` | Calculation frequency |
| `LOKI_URL` | `http://localhost:3100` | Loki instance URL |

## Running the Service

```bash
cd stacks/ai
docker-compose up health-score
```

## Output

Health scores are emitted to Loki every hour:

```json
{
  "score": 82,
  "grade": "B",
  "inventory_score": 85.0,
  "threat_score": 90.0,
  "change_score": 75.0,
  "hygiene_score": 80.0,
  "recommendations": [
    "Tag 3 unknown devices",
    "Review 1 high-severity anomaly"
  ]
}
```

## Grafana Dashboard

Create a dashboard showing:

### Primary Panel

- **Gauge**: Current score (0-100) with color coding
  - 90-100: Green
  - 70-89: Yellow
  - 0-69: Red

### Secondary Panels

- **Time series**: Score history (last 30 days)
- **Bar chart**: Component scores breakdown
- **Table**: Current recommendations
- **Stat panels**: Individual component scores

### Example Dashboard JSON

```json
{
  "panels": [
    {
      "title": "Security Health Score",
      "type": "gauge",
      "targets": [
        {
          "expr": "{service=\"health_score\"} | json | score"
        }
      ],
      "options": {
        "reduceOptions": {
          "values": false,
          "calcs": ["lastNotNull"]
        },
        "thresholds": {
          "mode": "absolute",
          "steps": [
            {"color": "red", "value": 0},
            {"color": "yellow", "value": 70},
            {"color": "green", "value": 90}
          ]
        }
      }
    }
  ]
}
```

## Loki Queries

```logql
# Current score
{service="health_score", stream="health_score"} | json | score

# Score history
{service="health_score"} | json | line_format "{{.score}}"

# Recommendations
{service="health_score"} | json | line_format "{{.recommendations}}"

# Component breakdown
{service="health_score"} | json | line_format "Inv:{{.inventory_score}} Thr:{{.threat_score}}"
```

## Interpretation

### Score 90-100 (Grade A)

- Excellent security posture
- All devices classified
- Minimal active threats
- Good hygiene practices

**Action**: Maintain current practices

### Score 80-89 (Grade B)

- Good security posture
- Minor issues to address
- Low threat activity

**Action**: Address recommendations

### Score 70-79 (Grade C)

- Acceptable security
- Several areas need attention
- Moderate risk

**Action**: Prioritize recommendations

### Score 60-69 (Grade D)

- Poor security posture
- Multiple significant issues
- Elevated risk

**Action**: Immediate attention required

### Score 0-59 (Grade F)

- Critical security issues
- High threat activity or major gaps
- Serious risk

**Action**: Emergency response needed

## Tuning

Adjust weights in `calculator.py` based on your priorities:

```python
WEIGHTS = {
    "inventory": 0.25,  # Increase if device management is critical
    "threat": 0.35,     # Increase if threat detection is priority
    "change": 0.20,     # Increase if change control is important
    "hygiene": 0.20,    # Increase if compliance is key
}
```

## Best Practices

1. **Set realistic hygiene flags**: Don't mark backups OK if they're not
2. **Monitor score trends**: Score direction matters more than absolute value
3. **Act on recommendations**: Use them as a work queue
4. **Review component scores**: Identify weak areas
5. **Set improvement goals**: Target specific grade improvements

## Example Scenarios

### Scenario 1: New Device Surge

- 10 new unknown devices appear
- Score drops from 85 to 70
- Inventory component: 60/100
- Recommendation: "Tag 10 unknown devices"

**Response**: Investigate and classify devices

### Scenario 2: Threat Event

- High-confidence intel match detected
- 3 high-severity anomalies
- Score drops from 88 to 75
- Threat component: 65/100

**Response**: Investigate threats, execute playbooks

### Scenario 3: Neglected Hygiene

- Backups haven't been verified
- Updates overdue
- Score: 70 (C)
- Hygiene component: 20/100

**Response**: Update systems, verify backups

## Future Enhancements

- [ ] Historical comparison (vs. last week/month)
- [ ] Peer comparison (if multiple sites)
- [ ] Predictive scoring (trend analysis)
- [ ] Custom weighting per environment
- [ ] Compliance framework mapping (NIST, CIS, etc.)
- [ ] Score breakdown by device/network segment
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

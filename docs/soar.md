# SOAR (Security Orchestration, Automation and Response)

## Overview

The SOAR module provides automated response capabilities through playbook-based rules that trigger actions when specific security events occur.

## Architecture

```
Security Events → Playbook Engine → Action Handlers → Effects
                      ↓
                 (Condition matching)
```

## Components

### Playbooks

Playbooks define automated responses to security events. Each playbook contains:

- **Match criteria**: Which event types to evaluate
- **Conditions**: Expressions that must be true for the playbook to trigger
- **Actions**: What to do when conditions match
- **Priority**: Execution order (higher runs first)
- **Dry-run flag**: Simulate without executing (for testing)

### Conditions

Conditions evaluate event data using these operators:

- `==`, `!=`: Equality/inequality
- `>`, `<`, `>=`, `<=`: Numeric comparison
- `contains`, `not_contains`: String/list containment
- `in`, `not_in`: Membership testing

Supports dot notation for nested fields: `metadata.risk_score >= 0.85`

### Actions

Available action types:

1. **BLOCK_DOMAIN**: Add domain to Pi-hole blocklist
   ```yaml
   type: BLOCK_DOMAIN
   params:
     domain: "${event.metadata.domain}"
   ```

2. **TAG_DEVICE**: Add tag to device in inventory
   ```yaml
   type: TAG_DEVICE
   params:
     device_id: "${event.device_id}"
     tag: "anomalous"
   ```

3. **SEND_NOTIFICATION**: Send alert via configured providers
   ```yaml
   type: SEND_NOTIFICATION
   params:
     subject: "Critical Alert"
     message: "Threat detected on network"
     severity: "CRITICAL"
   ```

4. **SIMULATE_ONLY**: Log what would happen (always dry-run)
   ```yaml
   type: SIMULATE_ONLY
   params:
     message: "Would block domain"
   ```

5. **LOG_EVENT**: Write to application log
   ```yaml
   type: LOG_EVENT
   params:
     message: "High-risk domain detected"
     level: "WARNING"
   ```

## Configuration

Playbooks are defined in `/etc/orion-ai/playbooks.yml` (or `config/playbooks.yml` in repo):

```yaml
playbooks:
  - id: alert-threat-intel
    name: "Alert on Threat Intel Match"
    enabled: true
    match_event_type: "intel_match"
    priority: 20
    dry_run: false
    conditions:
      - field: "severity"
        operator: "=="
        value: "CRITICAL"
    actions:
      - type: "SEND_NOTIFICATION"
        params:
          subject: "CRITICAL: Threat Intelligence Match"
          message: "Device contacted known malicious indicator"
          severity: "CRITICAL"
      - type: "TAG_DEVICE"
        params:
          device_id: "${event.device_id}"
          tag: "threat-intel-match"
```

## SOAR Service

The SOAR service runs periodically (default: every 5 minutes):

1. Fetches recent events from Loki (`stream="events"`)
2. Evaluates each event against all enabled playbooks
3. Executes matched actions (respecting dry-run settings)
4. Emits `soar_action` events documenting what was done

### Configuration

Environment variables:

```bash
# Global dry-run override (prevents all executions)
SOAR_DRY_RUN=false

# How often to run SOAR evaluation
SOAR_INTERVAL_MINUTES=5

# How far back to look for events
SOAR_LOOKBACK_MINUTES=10
```

## Dry-Run Mode

SOAR supports dry-run at two levels:

1. **Global**: Set `SOAR_DRY_RUN=true` to simulate all actions
2. **Per-playbook**: Set `dry_run: true` in playbook definition

Dry-run mode logs what would happen without executing actions. Use this to test playbooks before enabling them.

## Example Playbooks

### 1. Alert on New Devices

```yaml
- id: alert-new-device
  name: "Alert on New Device"
  enabled: true
  match_event_type: "new_device"
  conditions: []  # Match all new devices
  actions:
    - type: "SEND_NOTIFICATION"
      params:
        subject: "New Device Detected"
        message: "A new device joined the network"
        severity: "INFO"
```

### 2. Auto-Tag Anomalous Devices

```yaml
- id: tag-anomaly
  name: "Tag Anomalous Devices"
  enabled: true
  match_event_type: "device_anomaly"
  conditions:
    - field: "metadata.anomaly_score"
      operator: ">="
      value: 0.8
  actions:
    - type: "TAG_DEVICE"
      params:
        device_id: "${event.device_id}"
        tag: "anomalous"
```

### 3. Block High-Risk Domains

```yaml
- id: block-high-risk
  name: "Block High-Risk Domains"
  enabled: true
  match_event_type: "domain_risk"
  dry_run: true  # Test first!
  conditions:
    - field: "metadata.risk_score"
      operator: ">="
      value: 0.95
  actions:
    - type: "BLOCK_DOMAIN"
      params:
        domain: "${event.metadata.domain}"
```

## Notifications

SOAR integrates with the notifications module for alerting. Configured providers:

### Email (SMTP)

```bash
NOTIFY_SMTP_HOST=smtp.gmail.com
NOTIFY_SMTP_PORT=587
NOTIFY_SMTP_USER=your-email@gmail.com
NOTIFY_SMTP_PASS=your-app-password
NOTIFY_EMAIL_FROM=orion@yourdomain.com
NOTIFY_EMAIL_TO=admin@yourdomain.com
NOTIFY_SMTP_USE_TLS=true
```

### Webhook

```bash
NOTIFY_WEBHOOK_URL=https://your-webhook-url.com/endpoint
NOTIFY_WEBHOOK_TOKEN=your-optional-bearer-token
```

### Future Providers

- Signal (TODO)
- Telegram (TODO)

## Best Practices

1. **Start with dry-run**: Test new playbooks with `dry_run: true`
2. **Use priorities**: Order playbooks by severity (critical alerts first)
3. **Be specific**: Use precise conditions to avoid false positives
4. **Monitor actions**: Review `soar_action` events regularly
5. **Gradual rollout**: Enable playbooks one at a time
6. **Document playbooks**: Add clear names and comments

## Troubleshooting

**Playbook not triggering?**
- Check that `enabled: true`
- Verify event type matches `match_event_type`
- Test conditions individually
- Check SOAR service logs

**Action not executing?**
- Check for `SOAR_DRY_RUN=true` in environment
- Verify playbook doesn't have `dry_run: true`
- Check action handler logs for errors

**Performance issues?**
- Increase `SOAR_INTERVAL_MINUTES`
- Reduce `SOAR_LOOKBACK_MINUTES`
- Disable low-priority playbooks

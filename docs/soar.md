# SOAR-lite: Automated Response Playbooks

## Overview

The SOAR (Security Orchestration, Automation, and Response) module provides automated response capabilities based on security events.

## Architecture

### Components

1. **Playbook Engine** (`engine.py`): Evaluates events against playbook conditions
2. **Action Executor** (`actions.py`): Executes automated actions with safety controls
3. **SOAR Service** (`service.py`): Continuous monitoring loop

### Data Flow

```
Events (Loki) → Playbook Engine → Matched Playbooks → Action Executor → Results (Loki)
```

## Playbook Structure

Playbooks are defined in YAML (default: `config/playbooks.yml`):

```yaml
playbooks:
  - id: unique-playbook-id
    name: Human-Readable Name
    description: What this playbook does
    enabled: true
    match_event_type: intel_match  # Event type to match
    dry_run: true  # SAFETY: Simulate without executing
    priority: 100  # Higher priority runs first
    conditions:
      - field: fields.confidence
        operator: ">="
        value: 0.9
    actions:
      - action_type: BLOCK_DOMAIN
        parameters:
          domain: "{{fields.ioc_value}}"
          reason: "Automated block"
```

## Event Types

Playbooks can match these event types:

- `intel_match`: Threat intelligence matches
- `ai-device-anomaly`: AI-detected device anomalies
- `ai-domain-risk`: Risky domain detections
- `inventory_event`: Device inventory changes
- `change_event`: Behavioral changes
- `honeypot_hit`: Honeypot interactions
- `suricata_alert`: Suricata IDS alerts

## Available Actions

### BLOCK_DOMAIN

Block a domain via Pi-hole.

```yaml
- action_type: BLOCK_DOMAIN
  parameters:
    domain: malicious.example.com
    reason: "Threat intel match"
```

**Requirements**: Pi-hole API access (set `PIHOLE_URL` and `PIHOLE_API_KEY`)

### TAG_DEVICE

Add a tag to a device in inventory.

```yaml
- action_type: TAG_DEVICE
  parameters:
    device_ip: 192.168.1.50
    tag: suspicious
```

### SEND_NOTIFICATION

Send notification (via configured channel).

```yaml
- action_type: SEND_NOTIFICATION
  parameters:
    message: "Alert: Suspicious activity detected"
    severity: high  # low, medium, high, critical
```

**Note**: Notification channels (Signal/Telegram/Email) are TODO

### SIMULATE_ONLY

No-op action for testing.

```yaml
- action_type: SIMULATE_ONLY
  parameters:
    test: true
```

## Safety Features

### Dry Run Mode

**Global Dry Run** (recommended for initial deployment):

```bash
export SOAR_DRY_RUN=1
```

This prevents ALL actions from executing, regardless of playbook settings.

**Per-Playbook Dry Run**:

```yaml
playbooks:
  - id: my-playbook
    dry_run: true  # Only this playbook simulates
```

### Logging

All actions (executed or simulated) are logged:

- Console output shows dry run status
- Loki receives `soar_action` events with execution details

### Priority System

Playbooks with higher `priority` values run first. Use this to:

- Run blocking actions before notifications
- Ensure critical playbooks execute first

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOAR_DRY_RUN` | `1` | Global dry run mode (1=simulate, 0=execute) |
| `SOAR_POLL_INTERVAL` | `60` | How often to check for events (seconds) |
| `SOAR_PLAYBOOKS_FILE` | `/config/playbooks.yml` | Playbook configuration file |
| `SOAR_ALLOW_EMPTY_PLAYBOOKS` | `0` | Allow starting with no playbooks |
| `LOKI_URL` | `http://localhost:3100` | Loki instance URL |
| `PIHOLE_URL` | `http://192.168.1.2` | Pi-hole instance URL |
| `PIHOLE_API_KEY` | - | Pi-hole API key |

### Running the Service

**Docker Compose** (recommended):

```bash
cd stacks/ai
docker-compose up soar
```

**Standalone**:

```bash
export SOAR_DRY_RUN=1
export SOAR_PLAYBOOKS_FILE=./config/playbooks.yml
python -m orion_ai.soar.service
```

## Example Workflows

### Test Workflow (Safe)

1. Set `SOAR_DRY_RUN=1`
2. Create test playbook with low threshold
3. Trigger test events (manually or wait for real events)
4. Review logs to see what would be executed
5. Adjust playbook conditions

### Production Workflow

1. Test thoroughly in dry run mode
2. Start with high confidence thresholds (e.g., `confidence >= 0.9`)
3. Enable one playbook at a time
4. Monitor for false positives
5. Gradually lower thresholds or enable more playbooks

## Lab Mode

Tag devices with `lab` for testing:

```yaml
conditions:
  - field: fields.device_tags
    operator: contains
    value: lab
```

This allows aggressive actions on lab devices while keeping production devices safe.

## Monitoring

### Grafana Dashboards

Create panels showing:

- SOAR actions executed (by type)
- Dry run vs. executed ratio
- Playbook trigger frequency
- Action success/failure rates

### Loki Queries

```logql
# All SOAR actions
{service="soar", stream="soar_action"}

# Failed actions
{service="soar", stream="soar_action"} | json | success="false"

# Specific playbook
{service="soar", stream="soar_action"} | json | playbook_id="block-high-confidence-domains"
```

## Best Practices

1. **Always start in dry run mode**
2. **Test playbooks in lab environment first**
3. **Use high confidence thresholds initially**
4. **Monitor action logs closely**
5. **Have a rollback plan** (e.g., Pi-hole blacklist backups)
6. **Document playbook changes**
7. **Review false positives regularly**

## Troubleshooting

### Playbooks not triggering

- Check event type matches playbook `match_event_type`
- Verify conditions are correct (check field paths)
- Ensure playbook is `enabled: true`
- Check service logs for parsing errors

### Actions not executing

- Verify `SOAR_DRY_RUN` is set to `0`
- Check playbook `dry_run: false`
- Ensure required credentials are set (Pi-hole API key, etc.)
- Review action execution logs

### High false positive rate

- Increase confidence thresholds
- Add more specific conditions
- Review event data to understand patterns

## Future Enhancements

- [ ] Template variable resolution (`{{field.path}}`)
- [ ] Complex condition logic (AND/OR groups)
- [ ] Scheduled playbook execution
- [ ] External API integrations
- [ ] Action rollback/undo capabilities
- [ ] Machine learning for playbook tuning
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

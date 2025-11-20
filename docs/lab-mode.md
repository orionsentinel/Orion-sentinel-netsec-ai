# Lab Mode: Safe Testing Environment

## Overview

Lab mode allows you to test aggressive security policies on designated "lab" devices before applying them to production systems.

## Concept

In a home/lab environment, you often have:

- **Production devices**: Family devices, critical infrastructure
- **Lab devices**: Test machines, development systems, experimental setups

Lab mode enables:

1. More aggressive threat detection on lab devices
2. Lower blocking thresholds
3. Automated response testing
4. Risk-free policy validation

## Implementation

### Device Tagging

Tag lab devices in the inventory:

```python
from orion_ai.inventory.store import InventoryStore

store = InventoryStore()
store.tag_device("192.168.1.100", "lab")
store.tag_device("192.168.1.101", "lab")
```

Or via API:

```bash
curl -X POST http://localhost:8000/device/192.168.1.100/tag?tag=lab
```

### Lab-Specific Playbooks

Create playbooks that target lab devices:

```yaml
playbooks:
  - id: lab-aggressive-blocking
    name: Lab Mode - Aggressive Intel Blocking
    description: Lower threshold blocking for lab devices
    enabled: true
    match_event_type: intel_match
    dry_run: false
    priority: 75
    conditions:
      - field: fields.device_tags
        operator: contains
        value: lab
      - field: fields.confidence
        operator: ">="
        value: 0.5  # Lower than production (0.9)
    actions:
      - action_type: BLOCK_DOMAIN
        parameters:
          domain: "{{fields.ioc_value}}"
          reason: "Lab mode: Lower threshold blocking"
```

### Production Protection

Create playbooks that explicitly exclude lab devices:

```yaml
playbooks:
  - id: prod-conservative-blocking
    name: Production - Conservative Blocking
    enabled: true
    match_event_type: intel_match
    conditions:
      - field: fields.device_tags
        operator: contains
        value: lab
        negate: true  # NOT lab
      - field: fields.confidence
        operator: ">="
        value: 0.95  # Very high threshold
    actions:
      - action_type: BLOCK_DOMAIN
        parameters:
          domain: "{{fields.ioc_value}}"
```

## Configuration

### Environment Variables

```bash
# Define lab IP ranges (optional, for documentation)
export LAB_IP_RANGE="192.168.1.100-192.168.1.199"
export PROD_IP_RANGE="192.168.1.10-192.168.1.99"
```

### Network Segmentation (Optional)

For physical isolation, use VLANs:

- **VLAN 10**: Production (192.168.10.0/24)
- **VLAN 20**: Lab (192.168.20.0/24)

This prevents lab experiments from affecting production traffic.

## Lab Tag Hierarchy

Use multiple lab tags for granularity:

- `lab`: General lab device
- `lab-safe`: Isolated, safe to experiment on
- `lab-critical`: Lab device with production dependencies
- `lab-quarantine`: Temporarily isolated for testing

## Testing Workflow

### 1. Initial Testing (Dry Run)

```yaml
- id: test-new-policy
  enabled: true
  dry_run: true  # Simulate only
  conditions:
    - field: fields.device_tags
      operator: contains
      value: lab
```

**Action**: Review logs to see what would happen

### 2. Lab Execution

```yaml
- id: test-new-policy
  enabled: true
  dry_run: false  # Execute on lab
  conditions:
    - field: fields.device_tags
      operator: contains
      value: lab
```

**Action**: Execute on lab devices, monitor results

### 3. Production Rollout

```yaml
- id: prod-new-policy
  enabled: true
  dry_run: false
  conditions:
    # Remove or negate lab condition
    - field: fields.confidence
      operator: ">="
      value: 0.95
```

**Action**: Carefully enable for production

## Use Cases

### Testing New Playbooks

1. Create playbook targeting `lab` tag
2. Set lower thresholds or aggressive actions
3. Trigger test events (manually or wait)
4. Verify behavior
5. Adjust thresholds
6. Remove lab condition for production

### AI Model Validation

1. Tag test device as `lab`
2. Run new AI model against lab traffic
3. Compare alerts with baseline
4. Tune model parameters
5. Deploy to production once validated

### Honeypot Integration

1. Tag honeypot as `lab` or `honeypot`
2. Allow experimental deception techniques
3. Track attacker behavior
4. Learn patterns before applying defenses

### New Tool Evaluation

1. Deploy new security tool on lab device
2. Tag device appropriately
3. Monitor integration with Orion Sentinel
4. Validate log formats and alerts
5. Scale to production

## Safety Guardrails

Even in lab mode:

1. **Limit blast radius**: Ensure lab devices can't affect production
2. **Network isolation**: Use VLANs or firewall rules
3. **Rate limiting**: Prevent lab from generating excessive traffic
4. **Automatic rollback**: Have escape hatch for destructive tests
5. **Documentation**: Log all lab experiments

## Grafana Dashboards

Create lab-specific dashboards:

- Lab device activity
- Lab vs. production alert comparison
- Experiment tracking
- Lab policy effectiveness

## Example Lab Setup

### Lab Device Inventory

```python
lab_devices = [
    {"ip": "192.168.1.100", "hostname": "lab-ubuntu", "tags": ["lab", "linux"]},
    {"ip": "192.168.1.101", "hostname": "lab-windows", "tags": ["lab", "windows"]},
    {"ip": "192.168.1.102", "hostname": "lab-rpi", "tags": ["lab", "iot", "safe"]},
]
```

### Lab Playbook Set

```yaml
playbooks:
  # Aggressive AI threshold
  - id: lab-ai-anomaly-low-threshold
    match_event_type: ai-device-anomaly
    conditions:
      - field: fields.device_tags
        operator: contains
        value: lab
      - field: fields.anomaly_score
        operator: ">="
        value: 0.3  # vs. 0.8 for production
    actions:
      - action_type: TAG_DEVICE
        parameters:
          tag: anomalous-lab

  # Auto-block on honeypot hit
  - id: lab-honeypot-autoblock
    match_event_type: honeypot_hit
    conditions:
      - field: fields.src_ip
        operator: contains
        value: "192.168.1.1"  # Lab subnet
    actions:
      - action_type: BLOCK_DOMAIN
        # Block immediately in lab
```

## Best Practices

1. **Always tag lab devices**: Make it obvious what's in lab
2. **Start with dry run**: Even for lab
3. **Document experiments**: Note what you're testing and why
4. **Time-box tests**: Don't leave aggressive policies enabled indefinitely
5. **Review results**: Analyze what worked before moving to production
6. **Isolate network**: Prevent lab from impacting production
7. **Backup configurations**: Before destructive tests

## Transitioning to Production

### Checklist

- [ ] Policy tested in dry run mode
- [ ] Policy tested on lab devices
- [ ] No false positives observed
- [ ] Thresholds validated
- [ ] Documentation updated
- [ ] Rollback plan prepared
- [ ] Gradual rollout planned (if applicable)
- [ ] Monitoring dashboards ready
- [ ] Team notified

### Gradual Rollout

1. Enable for one production device
2. Monitor for 24-48 hours
3. Expand to small group
4. Monitor for 1 week
5. Full production deployment

## Future Enhancements

- [ ] Automatic lab/prod tag based on IP ranges
- [ ] Scheduled lab policy windows
- [ ] Lab simulation mode (replay production traffic in lab)
- [ ] Lab policy approval workflow
- [ ] Production policy inheritance from lab
- [ ] Compliance checking before prod deployment

# Honeypot & Deception Design

## Overview

This module provides integration for honeypot and deception technologies to detect and track malicious actors in the network.

## Architecture

### Honeypot Types

1. **Low-interaction honeypots** - Simple services that log connection attempts
   - SSH honeypot
   - HTTP/HTTPS honeypot
   - Telnet honeypot
   - SMTP honeypot

2. **Medium-interaction honeypots** - Emulated services with some interaction
   - Cowrie (SSH/Telnet)
   - Dionaea (multiple protocols)

### Integration with Orion Sentinel

Honeypots run as separate containers and forward logs to Loki with label `service="honeypot"`.

### Log Format

All honeypot hits should be logged to Loki with the following structure:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "src_ip": "203.0.113.42",
  "dst_port": 22,
  "honeypot_type": "ssh",
  "username": "admin",
  "password": "password123",
  "request_path": null,
  "user_agent": null,
  "protocol": "ssh",
  "session_id": "abc123",
  "commands": ["whoami", "ls -la"],
  "severity": "high"
}
```

### Labels for Loki

- `service="honeypot"`
- `honeypot_type="ssh|http|telnet|smtp"`
- `severity="low|medium|high|critical"`

## SOAR Integration

### Automatic Response

Honeypot hits trigger high-confidence alerts since any interaction with a honeypot is inherently suspicious.

Example playbooks:

1. **Immediate IP blocking**: IPs that hit honeypots are automatically blocked
2. **Escalated monitoring**: If a honeypot IP later appears in real traffic, alert immediately
3. **Threat intel correlation**: Cross-reference honeypot IPs with threat feeds

### Risk Scoring

Devices that contact honeypot-hitting IPs get elevated risk scores.

## Deployment

### Docker Compose Example

```yaml
services:
  cowrie-ssh:
    image: cowrie/cowrie:latest
    container_name: orion-honeypot-ssh
    ports:
      - "2222:2222"  # SSH honeypot on non-standard port
    environment:
      - COWRIE_BACKEND=json
    volumes:
      - ./honeypot-data/cowrie:/cowrie/var
    labels:
      - "orion.component=honeypot"
      - "orion.type=ssh"
  
  # Promtail to forward logs to Loki
  promtail-honeypot:
    image: grafana/promtail:latest
    container_name: orion-promtail-honeypot
    volumes:
      - ./honeypot-data:/var/log/honeypot:ro
      - ./config/promtail-honeypot.yml:/etc/promtail/config.yml:ro
    command: -config.file=/etc/promtail/config.yml
```

### Promtail Configuration

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: honeypot
    static_configs:
      - targets:
          - localhost
        labels:
          service: honeypot
          __path__: /var/log/honeypot/**/*.json
```

## Threat Intelligence Correlation

When a honeypot hit occurs:

1. Log to Loki with `service="honeypot"`
2. Threat intel module picks up the event
3. Source IP is added to internal IOC database
4. Future traffic from/to this IP is flagged
5. SOAR playbooks can auto-block or escalate

## Grafana Dashboards

Dashboard panels to include:

- **Honeypot Hits Timeline**: Visualize when hits occur
- **Top Source IPs**: Most active attackers
- **Attack Patterns**: Common usernames, passwords, commands
- **Geographic Distribution**: Where attacks originate
- **Honeypot vs Real Traffic**: Correlation between honeypot IPs and real network

## Security Considerations

1. **Isolation**: Honeypots must be isolated from production network
2. **Rate Limiting**: Prevent honeypot from being used for DDoS amplification
3. **Data Retention**: Limit retention of honeypot logs (PII concerns)
4. **Legal**: Ensure honeypot deployment complies with local laws

## Future Enhancements

- [ ] Active deception: Dynamic honeypot generation
- [ ] Honeytokens: Fake credentials in accessible locations
- [ ] Canary files: Monitored files that should never be accessed
- [ ] DNS canaries: Fake DNS records that alert when resolved
- [ ] Port knocking integration: Legitimate users can bypass

## Example: Simple HTTP Honeypot

A minimal Python HTTP honeypot example (see `simple_http_honeypot.py` for reference implementation).

## References

- [Cowrie SSH Honeypot](https://github.com/cowrie/cowrie)
- [Dionaea](https://github.com/DinoTools/dionaea)
- [Modern Honey Network](https://github.com/pwnlandia/mhn)

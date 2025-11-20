# Integration with orion-sentinel-dns-ha (Pi #1)

This document explains how this repository (`orion-sentinel-nsm-ai` on Pi #2) integrates with the DNS & Privacy stack (`orion-sentinel-dns-ha` on Pi #1).

## Integration Overview

```
┌─────────────────────┐                    ┌─────────────────────┐
│     Pi #1           │                    │      Pi #2          │
│   (DNS + HA)        │                    │   (NSM + AI)        │
│                     │                    │                     │
│  ┌──────────────┐   │  DNS Logs (3100)   │  ┌──────────────┐  │
│  │   Pi-hole    │   │ ──────────────────▶│  │    Loki      │  │
│  │   Unbound    │   │                    │  │              │  │
│  └──────────────┘   │                    │  └──────────────┘  │
│                     │                    │         │          │
│  ┌──────────────┐   │                    │         ▼          │
│  │  Promtail    │───┘                    │  ┌──────────────┐  │
│  │ (ships logs) │                        │  │ AI Service   │  │
│  └──────────────┘                        │  └──────┬───────┘  │
│                     │                    │         │          │
│  ┌──────────────┐   │ Pi-hole API (80)   │         │          │
│  │  Pi-hole API │◀──┼────────────────────┼─────────┘          │
│  │              │   │ (Block Domain)     │                    │
│  └──────────────┘   │                    │                    │
└─────────────────────┘                    └─────────────────────┘
```

There are two main integration points:

1. **DNS Log Shipping**: Pi #1 → Pi #2 (Promtail → Loki)
2. **Pi-hole API**: Pi #2 → Pi #1 (AI Service → Pi-hole)

---

## 1. DNS Log Shipping (Pi #1 → Pi #2)

### Purpose

Pi #2's AI service needs visibility into DNS queries to:
- Analyze domain patterns per device
- Detect suspicious domains (DGA, phishing)
- Correlate DNS with network flows from Suricata

### Architecture

On **Pi #1**, Promtail:
- Tails Pi-hole logs (`/var/log/pihole.log` or similar)
- Tails Unbound logs (if available)
- Ships logs to Pi #2's Loki HTTP endpoint

### Configuration on Pi #1

**Note**: This configuration should be added to the `orion-sentinel-dns-ha` repository, not this one. The details below are for reference.

#### Install Promtail on Pi #1

```bash
# On Pi #1
wget https://github.com/grafana/loki/releases/download/v2.9.3/promtail-linux-arm64.zip
unzip promtail-linux-arm64.zip
sudo mv promtail-linux-arm64 /usr/local/bin/promtail
sudo chmod +x /usr/local/bin/promtail
```

Or use Docker (recommended):

```yaml
# docker-compose.yml on Pi #1 (in orion-sentinel-dns-ha repo)
services:
  promtail:
    image: grafana/promtail:2.9.3
    container_name: promtail-dns-shipper
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/log/pihole:/var/log/pihole:ro
      - /var/log/unbound:/var/log/unbound:ro
    command: -config.file=/etc/promtail/config.yml
    restart: unless-stopped
```

#### Promtail Configuration on Pi #1

Create `promtail-config.yml` on Pi #1:

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://<PI2_IP>:3100/loki/api/v1/push
    # Replace <PI2_IP> with Pi #2's actual IP (e.g., 192.168.1.100)

scrape_configs:
  # Pi-hole logs
  - job_name: pihole
    static_configs:
      - targets:
          - localhost
        labels:
          job: pihole
          service: pihole
          pi: pi1-dns
          log_type: dns
          __path__: /var/log/pihole/pihole.log
    
    pipeline_stages:
      # Parse Pi-hole log format (dnsmasq)
      # Example: "Jan 15 10:30:00 dnsmasq[1234]: query[A] example.com from 192.168.1.50"
      - regex:
          expression: '^(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+dnsmasq\[\d+\]:\s+(?P<action>\w+)(\[(?P<query_type>\w+)\])?\s+(?P<domain>[\S]+)(\s+from\s+(?P<client_ip>[\d\.]+))?'
      - labels:
          action:
          query_type:
      - timestamp:
          source: timestamp
          format: "Jan 02 15:04:05"

  # Unbound logs (optional)
  - job_name: unbound
    static_configs:
      - targets:
          - localhost
        labels:
          job: unbound
          service: unbound
          pi: pi1-dns
          log_type: dns
          __path__: /var/log/unbound/unbound.log
    
    pipeline_stages:
      # Parse Unbound log format (varies by verbosity)
      - regex:
          expression: '^\[(?P<timestamp>[\d\-\s:]+)\]\s+unbound\[\d+:\d+\]\s+(?P<level>\w+):\s+(?P<message>.*)$'
      - labels:
          level:
```

**Key Configuration Points**:

1. **Client URL**: Points to Pi #2's Loki endpoint
   - Format: `http://<pi2-ip>:3100/loki/api/v1/push`
   - Ensure Pi #2's firewall allows port 3100 from Pi #1

2. **Labels**:
   - `service`: `pihole` or `unbound` (identifies log source)
   - `pi`: `pi1-dns` (identifies which Pi)
   - `log_type`: `dns` (helps filter in Grafana)

3. **Log Paths**:
   - Adjust `__path__` to match actual log file locations on Pi #1
   - Common Pi-hole paths:
     - `/var/log/pihole/pihole.log`
     - `/var/log/pihole/FTL.log`

4. **Pipeline Stages**:
   - `regex`: Parses log lines to extract fields
   - `labels`: Adds dynamic labels based on log content
   - `timestamp`: Extracts timestamp from log (optional)

#### Start Promtail on Pi #1

```bash
# If using Docker
docker compose up -d promtail

# If using systemd service
sudo systemctl start promtail
sudo systemctl enable promtail
```

### Firewall Configuration on Pi #2

Allow Loki ingestion from Pi #1:

```bash
# On Pi #2
sudo ufw allow from <PI1_IP> to any port 3100 comment "Loki from Pi #1"
```

Or if using iptables:

```bash
sudo iptables -A INPUT -p tcp -s <PI1_IP> --dport 3100 -j ACCEPT
```

### Verification

**On Pi #1**:
```bash
# Check Promtail logs
docker compose logs promtail

# Should see lines like:
# level=info msg="Successfully sent batch" ...
```

**On Pi #2**:
```bash
# Query Loki for DNS logs
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service="pihole"}' \
  | jq

# Should return log entries
```

**In Grafana (on Pi #2)**:
1. Explore → Loki
2. Query: `{service="pihole", pi="pi1-dns"}`
3. You should see DNS queries from Pi #1

### Expected Log Volume

**Estimate** (for a home network with 10-20 devices):
- **Pi-hole**: 5,000-20,000 queries/day → ~50-200 KB/day (uncompressed)
- **Unbound**: Depends on verbosity, usually 10-50 KB/day

Total: ~100-500 KB/day from Pi #1 → Pi #2.

Loki compresses logs, so actual storage is ~50-100 KB/day.

---

## 2. Pi-hole API Integration (Pi #2 → Pi #1)

### Purpose

When the AI service detects a high-risk domain, it can automatically add the domain to Pi-hole's blocklist via the API.

### Pi-hole API Overview

Pi-hole provides a simple HTTP API for blocklist management.

**Base URL**: `http://<pi1-ip>/admin/api.php`

**Common Endpoints**:

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `?list=black&add=<domain>&auth=<token>` | GET/POST | `domain`, `auth` | Add domain to blacklist |
| `?list=black&sub=<domain>&auth=<token>` | GET/POST | `domain`, `auth` | Remove domain from blacklist |
| `?status&auth=<token>` | GET | `auth` | Get Pi-hole status |
| `?summaryRaw&auth=<token>` | GET | `auth` | Get statistics |

**Authentication**:
- Requires API token (generated in Pi-hole admin UI)
- Token is passed via `auth` parameter

### Generating Pi-hole API Token (on Pi #1)

1. Access Pi-hole admin: `http://<pi1-ip>/admin`
2. Login with admin password
3. Settings → API / Web interface
4. Click "Show API token"
5. Copy token (long hex string)

**Security**:
- Store token securely (environment variable, not in code)
- Rotate token periodically
- Restrict API access to Pi #2's IP only (via firewall)

### Configuration on Pi #2

Edit `stacks/ai/.env`:

```bash
# Pi-hole API URL (on Pi #1)
PIHOLE_API_URL=http://192.168.1.10/admin/api.php  # Replace with Pi #1's IP

# Pi-hole API token
PIHOLE_API_TOKEN=abc123def456...  # Replace with actual token

# Enable/disable blocking
ENABLE_BLOCKING=true
```

### API Client Implementation

The AI service includes a Pi-hole API client in `src/orion_ai/pihole_client.py`.

**Example Usage**:

```python
from orion_ai.pihole_client import PiHoleClient

client = PiHoleClient(
    base_url="http://192.168.1.10/admin/api.php",
    api_token="your-token"
)

# Add domain to blacklist
success = client.add_domain("malicious.example.com", comment="AI detected: score=0.92")
if success:
    print("Domain blocked successfully")

# Remove domain
client.remove_domain("malicious.example.com")
```

**Error Handling**:
- Retries on network errors (exponential backoff)
- Logs all API calls and responses
- Returns `False` on failure (does not raise exceptions)

### Enforcement Policy

The AI service applies a policy to decide when to block:

```python
# In pipelines.py
def should_block(domain_risk_score: float, threshold: float = 0.85) -> bool:
    return domain_risk_score >= threshold
```

**Configurable Thresholds**:
- `DOMAIN_RISK_THRESHOLD=0.85`: Block domains with score >= 0.85
- Set higher (e.g., 0.95) for fewer false positives
- Set lower (e.g., 0.7) for more aggressive blocking

**Logging**:
All enforcement actions are logged to Loki:

```json
{
  "timestamp": "2024-01-15T10:35:00Z",
  "service": "ai-domain-risk",
  "severity": "critical",
  "domain": "malicious.example.com",
  "risk_score": 0.92,
  "action": "BLOCK",
  "pihole_response": "success",
  "pihole_api_url": "http://192.168.1.10/admin/api.php"
}
```

### Testing API Integration

#### Test Connectivity

```bash
# On Pi #2, test connection to Pi-hole API
curl "http://<pi1-ip>/admin/api.php?status&auth=<token>"

# Should return: {"status":"enabled"}
```

#### Test Adding a Domain

```bash
# Add test domain
curl "http://<pi1-ip>/admin/api.php?list=black&add=test.example.com&auth=<token>"

# Verify in Pi-hole UI: Settings → Blocklists
# Should see test.example.com in custom blacklist

# Remove test domain
curl "http://<pi1-ip>/admin/api.php?list=black&sub=test.example.com&auth=<token>"
```

#### Test from AI Service

```bash
# Run test script in container
docker compose run orion-ai python -c "
from orion_ai.pihole_client import PiHoleClient
import os

client = PiHoleClient(
    os.getenv('PIHOLE_API_URL'),
    os.getenv('PIHOLE_API_TOKEN')
)

# Add test domain
result = client.add_domain('test.ai-detected.com', comment='Test from AI service')
print(f'Add result: {result}')

# Remove test domain
result = client.remove_domain('test.ai-detected.com')
print(f'Remove result: {result}')
"
```

### Firewall Configuration on Pi #1

Restrict API access to Pi #2 only (recommended for security):

```bash
# On Pi #1
sudo ufw allow from <PI2_IP> to any port 80 comment "Pi-hole API from Pi #2"
```

Or use Pi-hole's built-in rate limiting (if available).

### Monitoring API Usage

**On Pi #2 (Grafana)**:

Query for enforcement actions:
```logql
{service="ai-domain-risk"} | json | action="BLOCK"
```

Dashboard panel: Count of blocked domains per day.

**On Pi #1 (Pi-hole UI)**:

1. Tools → Query Log
2. Filter by source: Pi #2's IP
3. Look for blocked queries from AI service

---

## Network Requirements

### Connectivity

- Pi #1 and Pi #2 must be on the same network (or routable subnets)
- DNS resolution between Pis (or use static IPs)
- Low latency (<10ms RTT recommended)

### Ports

| Source | Destination | Port | Protocol | Purpose |
|--------|-------------|------|----------|---------|
| Pi #1  | Pi #2       | 3100 | TCP      | Loki log ingestion |
| Pi #2  | Pi #1       | 80   | TCP      | Pi-hole API |
| Pi #2  | Pi #1       | 53   | UDP      | DNS queries (for normal operation) |

### Bandwidth

- **DNS Logs (Pi #1 → Pi #2)**: ~1-5 KB/minute (negligible)
- **Pi-hole API (Pi #2 → Pi #1)**: ~1-10 requests/minute (< 1 KB/min)

Total: <10 KB/minute between Pis.

---

## Security Considerations

### 1. API Token Security

- **Never commit tokens** to git repositories
- Store in `.env` file (excluded by `.gitignore`)
- Use environment variables in production
- Rotate tokens periodically (every 90 days)

### 2. Firewall Rules

- Restrict Loki (port 3100) to Pi #1's IP only
- Restrict Pi-hole API (port 80) to Pi #2's IP only
- Use `ufw` or `iptables` to enforce

### 3. TLS/HTTPS (Optional)

For added security:
- Configure Pi-hole to use HTTPS (requires certificate)
- Update `PIHOLE_API_URL` to use `https://`

### 4. Audit Logging

- All API calls are logged by AI service → Loki
- Periodically review enforcement actions in Grafana
- Alert on unusual API activity (e.g., >100 blocks/hour)

### 5. Rate Limiting

To prevent abuse:
- Limit Pi-hole API calls to 1 per second (configurable in AI service)
- Batch multiple domains if needed

---

## Troubleshooting

### DNS Logs Not Appearing on Pi #2

**Check on Pi #1**:
1. Promtail is running: `docker compose ps promtail`
2. Promtail can reach Loki: `curl http://<pi2-ip>:3100/ready`
3. Promtail logs for errors: `docker compose logs promtail`

**Check on Pi #2**:
1. Loki is running: `docker compose ps loki`
2. Firewall allows port 3100: `sudo ufw status`
3. Query Loki directly:
   ```bash
   curl -G "http://localhost:3100/loki/api/v1/query" \
     --data-urlencode 'query={service="pihole"}'
   ```

**Common Issues**:
- Wrong Pi #2 IP in Promtail config
- Firewall blocking port 3100
- Log file paths incorrect in Promtail config

### Pi-hole API Calls Failing

**Check**:
1. Pi-hole is accessible: `curl http://<pi1-ip>/admin`
2. API token is correct: `curl "http://<pi1-ip>/admin/api.php?status&auth=<token>"`
3. Firewall allows port 80 from Pi #2

**Debug**:
```bash
# Check AI service logs
docker compose logs orion-ai | grep pihole

# Test API call manually
curl "http://<pi1-ip>/admin/api.php?list=black&add=test.com&auth=<token>"
```

**Common Issues**:
- Wrong API token
- Pi-hole not running on Pi #1
- Network firewall blocking Pi #2 → Pi #1 on port 80

### Blocked Domains Not Actually Blocked

**Verify**:
1. Check Pi-hole blocklist: Settings → Blocklists (in Pi-hole UI)
2. Test DNS query:
   ```bash
   dig @<pi1-ip> malicious.example.com
   ```
   Should return `0.0.0.0` or Pi-hole's blocking IP

3. Check Pi-hole logs: Tools → Query Log

**Possible Causes**:
- Domain added to wrong blocklist group
- DNS clients not using Pi #1 as resolver
- DNS caching on client side

---

## Data Flow Summary

### Startup Sequence

1. Pi #1 boots → Pi-hole + Unbound start
2. Pi #1 Promtail starts → begins tailing logs
3. Pi #2 boots → Loki + Grafana start
4. Pi #1 Promtail connects to Pi #2 Loki → starts shipping logs
5. Pi #2 AI service starts → begins querying Loki for logs
6. Pi #2 AI detects high-risk domain → calls Pi #1 Pi-hole API

### Ongoing Operation

**Every 10 minutes** (configurable):
1. AI service queries Loki for last 10 minutes of NSM + DNS logs
2. Extracts features, runs models
3. Identifies anomalies and high-risk domains
4. For domains with risk score >= 0.85:
   - Calls Pi-hole API to add to blocklist
   - Logs enforcement action to Loki
5. Writes all detection results to Loki (via Promtail)

**Continuous**:
- Pi #1 Promtail ships DNS logs to Pi #2 Loki in real-time
- Suricata on Pi #2 writes NSM logs → Promtail → Loki
- Grafana displays all logs in dashboards

---

## Future Enhancements

1. **Bidirectional Communication**:
   - Pi #1 could query Pi #2 for AI insights
   - Expose AI service API on Pi #2 for external queries

2. **Distributed Loki**:
   - Run Loki in microservices mode across both Pis
   - Better scalability and redundancy

3. **Shared Blocklist**:
   - Sync Pi-hole blocklists across multiple Pi #1 instances (if running multiple DNS Pis)

4. **Webhook Alerts**:
   - Pi #2 sends webhook to Pi #1 for critical events
   - Pi #1 could trigger additional actions (notifications, etc.)

---

**See Also**:
- [architecture.md](architecture.md) for overall system design
- [ai-stack.md](ai-stack.md) for AI service details
- [pi2-setup.md](pi2-setup.md) for Pi #2 setup instructions

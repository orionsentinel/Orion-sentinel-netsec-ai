# Sample Data for Development and Testing

This directory contains synthetic sample data for developing and testing Orion Sentinel without needing a live network environment.

## Files

### `suricata-eve.json`
Sample Suricata IDS alerts in EVE JSON format (one JSON object per line).

**Contains:**
- Network alerts (suspicious traffic patterns)
- DNS queries and responses
- HTTP requests
- TLS connections
- Various signature matches (Tor, malware, scanning, etc.)

**Event types:**
- `alert`: IDS signature matches
- `dns`: DNS queries and answers
- `http`: HTTP transactions

**Use cases:**
- Test Loki log ingestion
- Develop Grafana dashboards
- Validate AI anomaly detection pipelines
- Test SOAR playbook triggers

### `pihole-dns.log`
Sample Pi-hole DNS query log in simplified text format.

**Contains:**
- Normal DNS queries (Google, GitHub, Netflix, etc.)
- Blocked queries (ads, trackers, malicious domains)
- Mix of A and AAAA record lookups
- PTR (reverse DNS) queries

**Format:** `timestamp client query_type domain response_type response`

**Use cases:**
- Test DNS log parsing
- Validate domain risk scoring
- Test Pi-hole integration
- Develop DNS-based dashboards

### `intel_matches.json`
Sample threat intelligence match events.

**Contains:**
- IOC matches from various sources:
  - AlienVault OTX (Open Threat Exchange)
  - URLhaus (malicious URLs)
  - PhishTank (phishing sites)
  - Feodo Tracker (botnet C2)
  - Tor exit nodes
  - Custom blocklists

**Fields:**
- `indicator_type`: domain, ip, hash, etc.
- `threat_type`: C2, phishing, malware, DGA, etc.
- `confidence`: 0.0-1.0 score
- `severity`: low, medium, high, critical
- `matched_event`: The original event that triggered the match

**Use cases:**
- Test threat intel correlation
- Validate risk score boosting
- Test SOAR response to high-confidence matches
- Develop intel-focused dashboards

## Using Sample Data

### With Dev Compose Stack

Start the development environment with log injector:

```bash
cd stacks/nsm
docker compose -f docker-compose.dev.yml up -d
```

The log injector service will:
1. Read sample files from `samples/`
2. Parse and normalize them
3. Push to Loki with appropriate labels
4. Loop continuously for ongoing testing

### Manual Testing

Push sample data to Loki manually:

```bash
# Install logcli (Loki CLI tool)
# wget https://github.com/grafana/loki/releases/download/v2.8.0/logcli-linux-amd64.zip
# unzip logcli-linux-amd64.zip
# chmod +x logcli-linux-amd64

# Push Suricata events
cat samples/suricata-eve.json | while read line; do
  echo "$line" | ./logcli-linux-amd64 push \
    --stdin \
    --server=http://localhost:3100 \
    --label=job=suricata \
    --label=host=dev
done
```

Or use Python with the AI service's Loki client:

```python
from orion_ai.output_writer import LokiWriter

writer = LokiWriter(loki_url="http://localhost:3100")

# Read and push samples
import json
with open("samples/suricata-eve.json") as f:
    for line in f:
        event = json.loads(line)
        writer.write_log(
            labels={"job": "suricata", "host": "dev", "event_type": event["event_type"]},
            message=line
        )
```

### Query Sample Data in Grafana

After pushing sample data, query it in Grafana:

**LogQL queries:**
```logql
# All Suricata events
{job="suricata"}

# Only alerts
{job="suricata"} | json | event_type="alert"

# High severity alerts
{job="suricata"} | json | event_type="alert" | severity <= 2

# Specific source IP
{job="suricata"} | json | src_ip="192.168.1.100"

# DNS queries to malicious domains
{job="dns"} | json | line_format "{{.domain}}" |~ "malicious|c2-server|phishing"
```

**Example dashboard panels:**
- Alert count by severity (bar chart)
- Top source IPs (table)
- DNS query rate over time (graph)
- Threat intel match timeline (logs panel)

## Customizing Sample Data

### Adding More Events

Edit the sample files to add your own test data:

**Suricata format (JSON per line):**
```json
{
  "timestamp": "2025-01-20T15:00:00+0000",
  "event_type": "alert",
  "src_ip": "192.168.1.99",
  "dest_ip": "10.0.0.1",
  "alert": {
    "signature": "Custom Test Alert",
    "severity": 2
  }
}
```

**Pi-hole format (space-separated):**
```
2025-01-20 15:00:00 192.168.1.99 A test.example.com IP 1.2.3.4
```

**Intel matches format (JSON array):**
```json
{
  "timestamp": "2025-01-20T15:00:00+0000",
  "source": "custom",
  "indicator_type": "domain",
  "indicator_value": "test.example.com",
  "threat_type": "testing",
  "confidence": 0.5,
  "severity": "low"
}
```

### Generating Large Datasets

Use the provided generator script (if available) or create your own:

```bash
# Generate 1000 random Suricata alerts
python scripts/generate_sample_data.py --type suricata --count 1000 > samples/large_dataset.json
```

Or use a simple bash loop:

```bash
# Generate 100 DNS queries with random IPs
for i in {1..100}; do
  IP="192.168.1.$((RANDOM % 254 + 1))"
  DOMAIN="test$i.example.com"
  echo "2025-01-20 15:00:$i $IP A $DOMAIN IP 1.2.3.4"
done > samples/dns_bulk.log
```

## Sample Data Limitations

**These samples are for testing only:**
- Synthetic data, not real network traffic
- Limited variety (only ~50 events across all files)
- IP addresses use reserved ranges (192.168.1.x, 203.0.113.x, etc.)
- Domains are example.com or obviously fake
- No correlation with real threat intelligence

**For production-like testing:**
- Capture real traffic in a lab environment
- Use publicly available packet captures (PCAPs)
- Generate traffic with tools like `scapy` or `nmap`
- Replay historical logs from a backup

## Security Note

These sample files intentionally contain "malicious" looking data (domains, IPs, signatures). They are:
- **Safe to use**: No real malware or exploits
- **Synthetic**: Generated for testing purposes
- **Non-routable**: Using reserved IP ranges
- **Educational**: Meant to demonstrate detection capabilities

Do not use production data with real user information in sample files (privacy/security risk).

## Related Documentation

- [Operations Guide](../docs/operations.md): Development mode section
- [Logging & Dashboards](../docs/logging-and-dashboards.md): Loki and Grafana usage
- [AI Stack](../docs/ai-stack.md): AI service pipelines that consume this data

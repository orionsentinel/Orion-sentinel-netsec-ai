# Sample Data for Development

This directory contains synthetic sample data for testing and development of the Orion Sentinel NSM+AI system.

## Files

### suricata-eve.json
Synthetic Suricata IDS alerts in EVE JSON format (Extensible Event Format).

**Contains:**
- Network intrusion detection alerts
- DNS query/response events
- HTTP transaction logs
- File detection events
- TLS certificate observations
- Flow metadata

**Event types represented:**
- `alert` - IDS signature matches
- `dns` - DNS queries and responses
- `http` - HTTP transactions
- `fileinfo` - File transfers and downloads
- `flow` - Network flow summaries

**Use cases:**
- Testing Grafana dashboards
- Developing SOAR playbooks
- Validating anomaly detection
- Training ML models

### pihole-dns.log
Synthetic Pi-hole DNS query logs in dnsmasq log format.

**Contains:**
- DNS queries (A, AAAA, PTR records)
- Forwarded queries to upstream DNS
- Blocked queries (ads, trackers, malware)
- DNS responses

**Domains included:**
- Legitimate domains (google.com, github.com, etc.)
- Blocked ad/tracker domains
- Malicious domains (C2, phishing, cryptomining)

**Use cases:**
- Testing DNS monitoring dashboards
- Validating Pi-hole integration
- Testing domain-based SOAR rules
- DNS traffic analysis

### intel_matches.json
Synthetic threat intelligence correlation results.

**Contains:**
- Matches between observed activity and threat indicators
- Various indicator types (domains, IPs, file hashes, JA3, user agents)
- Confidence scores and severity levels
- Threat categorization

**Threat categories represented:**
- Malware C2 communications
- Phishing sites
- Tor exit nodes
- Cryptomining
- DGA (Domain Generation Algorithm) domains
- Exploit attempts (e.g., Log4Shell)
- Ransomware infrastructure

**Use cases:**
- Testing high-severity alert workflows
- Validating SOAR automation
- Dashboard development
- Threat intelligence correlation testing

## Usage

### With Development Environment

Start the dev environment with sample data injection:

```bash
cd stacks/nsm
docker compose -f docker-compose.dev.yml up -d
```

The `log-injector` service will automatically:
1. Wait for Loki to be ready
2. Read sample files from this directory
3. Push logs to Loki with appropriate labels every 30 seconds
4. Simulate continuous log ingestion

### Manual Testing

You can also manually push sample data to Loki:

```bash
# Install jq if needed
apt-get install jq

# Push Suricata events
cat samples/suricata-eve.json | while read line; do
  echo "$line" | jq -c '{streams: [{stream: {job: "suricata", source: "test"}, values: [[(now | tostring), .]]}]}' | \
  curl -H "Content-Type: application/json" -XPOST -s "http://localhost:3100/loki/api/v1/push" -d @-
done
```

### Modifying Sample Data

Feel free to edit these files to add your own test scenarios:

1. **Add new events**: Append new JSON lines (for .json files) or log lines (for .log files)
2. **Change severity**: Adjust confidence scores or threat categories
3. **Test edge cases**: Add malformed data or unusual patterns
4. **Customize IPs**: Use your own test IP ranges

**Format guidelines:**
- `suricata-eve.json`: One JSON object per line (newline-delimited JSON)
- `pihole-dns.log`: Standard syslog/dnsmasq format
- `intel_matches.json`: One JSON object per line

## Integration with Services

### SOAR Testing

Test playbooks against sample data:

1. Edit `config/playbooks.yml` with test rules
2. Set `SOAR_DRY_RUN=1` in AI stack
3. Start dev environment
4. Monitor SOAR logs: `docker compose -f ../ai/docker-compose.yml logs -f soar`

### Grafana Dashboard Development

1. Start dev environment
2. Access Grafana at http://localhost:3000
3. Query sample data using LogQL
4. Build and test dashboards
5. Export as JSON and save to `stacks/nsm/grafana/dashboards/`

### Anomaly Detection Testing

Sample data includes patterns that should trigger various detections:

- Multiple alerts from same source IP (potential compromise)
- High-confidence intel matches (malware C2)
- Unusual DNS patterns (DGA domains)
- Exploit attempts (Log4Shell)

## Adding New Sample Files

To add new sample data:

1. Create file in `samples/` directory
2. Follow existing format (JSON lines or text logs)
3. Update `stacks/nsm/log-injector.sh` to inject new file
4. Document in this README

## Notes

- **Not real data**: All IPs, domains, and events are synthetic
- **Safe to commit**: No sensitive information
- **Reproducible**: Same data on every injection cycle
- **Labeled appropriately**: All logs tagged with `environment="dev"`

## See Also

- [Operations Guide](../docs/operations.md) - Full dev environment setup
- [SOAR Guide](../docs/soar.md) - Playbook development
- [Architecture](../docs/architecture.md) - System overview

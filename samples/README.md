# Sample Data for Development and Testing

This directory contains synthetic test data for developing and testing Orion Sentinel components without requiring a live network or actual security events.

## Files

### `suricata-eve.json`

Synthetic Suricata EVE (Extensible Event Format) JSON logs containing various alert types.

**Event Types Included:**
- Network alerts (suspicious traffic patterns)
- DNS queries
- HTTP requests
- SSH connection attempts
- Flow records

**Sample Threat Signatures:**
- `GPL ATTACK_RESPONSE id check returned root`
- `ET TOR Known Tor Exit Node Traffic`
- `ET POLICY Possible Suspicious User-Agent`
- `ET SCAN Potential SSH Scan`

**Format:** NDJSON (newline-delimited JSON) - one event per line

**Usage:**
```bash
# View formatted
cat samples/suricata-eve.json | jq .

# Filter specific event types
cat samples/suricata-eve.json | jq 'select(.event_type == "alert")'

# Count events by type
cat samples/suricata-eve.json | jq -r '.event_type' | sort | uniq -c
```

### `pihole-dns.log`

Dummy Pi-hole DNS query logs in dnsmasq format.

**Query Types:**
- Normal DNS queries (allowed domains)
- Blocked queries (ads, trackers, malware)
- NXDOMAIN responses (non-existent domains)
- PTR lookups (reverse DNS)
- IPv6 AAAA queries
- TXT record queries

**Notable Entries:**
- Blocked ads: `doubleclick.net`, `malicious-ad-tracker.com`
- Blocked malware: `known-malware-c2.evil`
- Suspicious DGA domain: `suspicious-dga-domain-12345abcdef.com`

**Format:** Standard syslog-style dnsmasq logs

**Usage:**
```bash
# View all queries
cat samples/pihole-dns.log

# Show only blocked domains
grep "is 0.0.0.0" samples/pihole-dns.log

# Show forwarded queries
grep "forwarded" samples/pihole-dns.log

# Count queries per client IP
grep "query" samples/pihole-dns.log | awk '{print $10}' | sort | uniq -c
```

### `intel_matches.json`

Sample threat intelligence match events from various sources.

**Threat Intel Sources:**
- `alienvault_otx`: AlienVault Open Threat Exchange
- `feodo_tracker`: abuse.ch Feodo Tracker (botnet C2)
- `urlhaus`: abuse.ch URLhaus (malware URLs)
- `phishtank`: PhishTank (verified phishing sites)

**Threat Types:**
- C2 servers
- Botnet infrastructure
- Malware distribution sites
- Phishing domains
- Tor exit nodes
- Malicious file hashes

**Format:** JSON array of match objects

**Usage:**
```bash
# View formatted
cat samples/intel_matches.json | jq .

# Filter by threat type
cat samples/intel_matches.json | jq '.[] | select(.threat_type == "C2")'

# Show high-confidence matches only
cat samples/intel_matches.json | jq '.[] | select(.confidence > 0.9)'

# Group by source
cat samples/intel_matches.json | jq -r '.[].source' | sort | uniq -c
```

## Using Sample Data in Development

### Dev Environment

The dev environment uses these samples to populate Loki with realistic data:

```bash
cd stacks/nsm
docker compose -f docker-compose.dev.yml up -d
```

See `docs/operations.md` for full dev mode documentation.

### Manual Testing

**Inject into Loki manually:**

```bash
# Example: Push Suricata logs to Loki
# (Requires promtail or log injection script)

# Using curl to Loki API
cat samples/suricata-eve.json | while read line; do
  curl -X POST http://localhost:3100/loki/api/v1/push \
    -H "Content-Type: application/json" \
    -d "{
      \"streams\": [{
        \"stream\": {\"job\": \"suricata\", \"level\": \"info\"},
        \"values\": [[\"$(date +%s)000000000\", \"$line\"]]
      }]
    }"
done
```

**Test AI detection pipeline:**

```python
# Example Python usage
import json

# Load sample data
with open('samples/suricata-eve.json') as f:
    for line in f:
        event = json.loads(line)
        # Process event...
        print(f"Event: {event['event_type']} from {event['src_ip']}")
```

### Extending Sample Data

**To add your own samples:**

1. **Sanitize real data:**
   - Replace real IPs with RFC 5737 test addresses (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24)
   - Replace real domains with example.com, example.org, or fictional domains
   - Remove any personally identifiable information

2. **Follow the format:**
   - Suricata: NDJSON with standard EVE JSON schema
   - Pi-hole: dnsmasq log format
   - Intel matches: JSON array with consistent structure

3. **Document in this README:**
   - Add description of new sample file
   - Include usage examples
   - Note any special fields or scenarios covered

## Sample Data Scenarios

### Scenario 1: Botnet Infection

Device `192.168.1.50` exhibits botnet-like behavior:
- Connects to known C2 IP `203.0.113.42` (Emotet) - see `suricata-eve.json`
- Triggers alert `GPL ATTACK_RESPONSE id check returned root`
- Matches Feodo Tracker intel - see `intel_matches.json`

### Scenario 2: Tor Usage

Device `192.168.1.75` connects to Tor network:
- Connection to Tor exit node `185.220.101.1` - see `suricata-eve.json`
- Alert `ET TOR Known Tor Exit Node Traffic`
- Blocked ad domain `doubleclick.net` - see `pihole-dns.log`

### Scenario 3: Malware Download Attempt

Device `192.168.1.100` attempts to download malware:
- HTTP GET to `/download/payload.exe` on suspicious domain - see `suricata-eve.json`
- Alert `ET POLICY Possible Suspicious User-Agent`
- Domain matches URLhaus intel - see `intel_matches.json`

### Scenario 4: DGA Activity

Device `192.168.1.150` queries algorithmically generated domain:
- DNS query for `suspicious-dga-domain-12345abcdef.com` (NXDOMAIN) - see `pihole-dns.log`
- Possible botnet attempting to reach C2
- Multiple similar queries would indicate DGA pattern

### Scenario 5: SSH Scan

Device `192.168.1.200` appears to be conducting SSH port scan:
- Alert `ET SCAN Potential SSH Scan` - see `suricata-eve.json`
- Queries known malware C2 domain (blocked by Pi-hole) - see `pihole-dns.log`
- Matches PhishTank intel - see `intel_matches.json`

## Data Format References

**Suricata EVE JSON:**
- [Suricata EVE Documentation](https://suricata.readthedocs.io/en/latest/output/eve/eve-json-output.html)

**Pi-hole/dnsmasq Logs:**
- [Pi-hole Documentation](https://docs.pi-hole.net/)
- [dnsmasq Manual](https://thekelleys.org.uk/dnsmasq/doc.html)

**Threat Intel Sources:**
- [AlienVault OTX](https://otx.alienvault.com/)
- [abuse.ch URLhaus](https://urlhaus.abuse.ch/)
- [abuse.ch Feodo Tracker](https://feodotracker.abuse.ch/)
- [PhishTank](https://www.phishtank.com/)

## Privacy & Ethics

⚠️ **Important:**

- All IP addresses in these samples use RFC 5737 test ranges or public examples
- All domains are fictional or use example.com/example.org
- No real network traffic or personal data is included
- When creating your own samples from real data, always sanitize thoroughly

## Contributing Samples

If you create useful sample data scenarios:

1. Ensure all data is synthetic or sanitized
2. Document the scenario in this README
3. Follow existing format conventions
4. Submit via pull request

---

**For more information on development workflows, see:**
- [Operations Guide](../docs/operations.md#development-mode)
- [Architecture Documentation](../docs/architecture.md)

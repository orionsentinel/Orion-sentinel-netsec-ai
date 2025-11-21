# Threat Intelligence Integration

Orion Sentinel integrates real-time threat intelligence from multiple reputable sources to enhance detection accuracy and provide context for security events.

## Overview

Threat intelligence (TI) enriches your security monitoring by:

- **Identifying Known Threats**: Automatically flag domains/IPs/URLs seen in active campaigns
- **Boosting Risk Scores**: Increase confidence in AI detections when IOCs match
- **Providing Context**: Explain *why* something is suspicious (e.g., "Matched Feodo C2")
- **Reducing False Positives**: Higher confidence in blocking decisions
- **Attribution**: Link activity to specific malware families or threat actors

## Supported Feeds

### 🛡️ AlienVault OTX (Open Threat Exchange)

**Type**: Community-driven threat intelligence  
**Content**: Domains, IPs, URLs, hashes from security researchers  
**API Key**: Required (free registration)  
**Update Frequency**: Real-time  
**Quality**: High (vetted community)

**Sign Up**: [https://otx.alienvault.com](https://otx.alienvault.com)

```bash
# .env
TI_ENABLE_OTX=true
TI_OTX_API_KEY=your-otx-api-key-here
```

### 🚨 abuse.ch URLhaus

**Type**: Malicious URL database  
**Content**: Active malware distribution sites, phishing URLs  
**API Key**: Not required  
**Update Frequency**: Real-time  
**Quality**: Very High (verified by abuse.ch)

```bash
# .env
TI_ENABLE_URLHAUS=true
```

**Data Source**: [https://urlhaus.abuse.ch](https://urlhaus.abuse.ch)

### 🤖 abuse.ch Feodo Tracker

**Type**: Botnet C2 tracker  
**Content**: IP addresses of active botnet command & control servers  
**Covers**: Dridex, Emotet, TrickBot, QakBot, BazarLoader  
**API Key**: Not required  
**Update Frequency**: Real-time  
**Quality**: Very High (honeypot-verified)

```bash
# .env
TI_ENABLE_FEODO=true
```

**Data Source**: [https://feodotracker.abuse.ch](https://feodotracker.abuse.ch)

### 🎣 PhishTank

**Type**: Verified phishing site database  
**Content**: URLs of confirmed phishing attacks  
**API Key**: Optional (higher rate limits)  
**Update Frequency**: Hourly  
**Quality**: High (community-verified)

```bash
# .env
TI_ENABLE_PHISHTANK=true
TI_PHISHTANK_API_KEY=optional-key-for-higher-limits
```

**Data Source**: [https://www.phishtank.com](https://www.phishtank.com)

## How It Works

### 1. Threat Intelligence Sync

IOCs are periodically fetched from enabled feeds and stored locally:

```bash
# Manual sync (run in container)
python -m orion_ai.threat_intel.sync --hours 24

# Check IOC store statistics
python -m orion_ai.threat_intel.sync --stats
```

**Storage**: SQLite database at `/data/threat_intel.db`

**Retention**: 90 days (configurable in code)

### 2. Real-Time Lookup

When AI detects suspicious activity:

1. Extract domains/IPs from event
2. Lookup in local IOC store (fast SQLite query)
3. If match found:
   - Add IOC info to event metadata
   - Boost risk score based on confidence
   - Add human-readable reason (e.g., "Matched Feodo C2")
4. Event enriched with TI context

### 3. Event Enrichment

Events automatically include TI context:

```json
{
  "event_type": "domain_risk",
  "title": "High-Risk Domain Detected",
  "metadata": {
    "domain": "evil.example.com",
    "risk_score": 0.95,
    "ioc_matches": [
      {
        "type": "domain",
        "value": "evil.example.com",
        "source": "abuse.ch_urlhaus",
        "confidence": 0.9
      }
    ],
    "ti_sources": ["abuse.ch_urlhaus"],
    "reasons": [
      "Matched domain evil.example.com in abuse.ch_urlhaus (confidence: 0.90)",
      "Known malware distribution site"
    ],
    "ti_boost": 0.27
  }
}
```

## Setup Guide

### 1. Enable Feeds

Edit `.env`:

```bash
# Enable all free feeds
TI_ENABLE_URLHAUS=true
TI_ENABLE_FEODO=true
TI_ENABLE_PHISHTANK=true

# Optional: AlienVault OTX (requires API key)
TI_ENABLE_OTX=false
TI_OTX_API_KEY=
```

### 2. Initial Sync

Run first sync to populate IOC store:

```bash
cd stacks/ai
docker-compose exec ai-service python -m orion_ai.threat_intel.sync --hours 168
```

**Note**: First sync may take several minutes depending on feeds enabled.

### 3. Automate Sync

Add to crontab or systemd timer:

```bash
# Sync every 4 hours
0 */4 * * * cd /path/to/stacks/ai && docker-compose exec -T ai-service python -m orion_ai.threat_intel.sync --hours 4
```

Or use a scheduled container:

```yaml
# docker-compose.yml
services:
  ti-sync:
    image: orion-ai:latest
    command: >
      sh -c "while true; do 
        python -m orion_ai.threat_intel.sync --hours 4;
        sleep 14400;
      done"
    volumes:
      - ./data:/data
    env_file:
      - .env
```

### 4. Verify Integration

Check IOC store stats:

```bash
docker-compose exec ai-service python -m orion_ai.threat_intel.sync --stats
```

Expected output:

```
IOC Store Statistics:
  Total IOCs: 15,234
    domain: 8,456
    ip: 5,123
    url: 1,655
  Total matches: 42
  Matches (24h): 3
```

## Integration Points

### AI Detection Pipeline

TI lookup is automatically integrated into:

- **Domain Risk Scoring**: Check domains against IOC feeds
- **Device Anomaly Detection**: Flag devices contacting known bad IPs
- **DNS Analysis**: Identify queries to malicious domains

**Implementation**:

```python
from orion_ai.threat_intel.lookup import enrich_event_with_ti

# Enrich event with TI before SOAR processing
event_data = {...}
enriched_event = enrich_event_with_ti(event_data)
```

### SOAR Playbooks

Use TI matches as playbook conditions:

```yaml
playbooks:
  - id: block-on-ti-match
    name: "Block Domain on Threat Intel Match"
    enabled: true
    match_event_type: "domain_risk"
    conditions:
      - field: "metadata.ti_matched"
        operator: "=="
        value: true
      - field: "metadata.ioc_matches.0.confidence"
        operator: ">="
        value: 0.8
    actions:
      - type: "BLOCK_DOMAIN"
        params:
          domain: "${event.metadata.domain}"
      - type: "SEND_NOTIFICATION"
        params:
          subject: "Blocked Domain from Threat Intel"
          severity: "CRITICAL"
```

### Notifications

TI context is included in all notifications:

```
🚨 Orion Sentinel Alert

High-Risk Domain Detected

Severity: CRITICAL
Time: 2024-11-21 20:15:00

Device 192.168.1.50 contacted a known malicious domain.

Threat Intelligence:
  • Matched domain evil.example.com (source: abuse.ch_urlhaus)
  • Sources: abuse.ch_urlhaus
  • Malware Family: Emotet
  • Threat Type: malware

Risk Score: 0.95
```

## IOC Data Model

Each IOC includes:

- **Value**: Domain, IP, URL, or hash
- **Type**: Domain, IP, URL, hash_md5, hash_sha256, etc.
- **Source**: Which feed it came from
- **First Seen / Last Seen**: Temporal tracking
- **Confidence**: 0.0 to 1.0 (source-dependent)
- **Threat Type**: malware, c2, phishing, botnet, ransomware, etc.
- **Tags**: Additional classification
- **Malware Family**: If applicable (e.g., "Emotet", "TrickBot")

## Performance

### Lookup Speed

- **SQLite with indexes**: ~0.1ms per lookup
- **Bulk lookup**: 100 domains in ~10ms
- **Store size**: ~50-100 MB for 50,000 IOCs

### Sync Performance

- **URLhaus**: ~2-5 seconds for 1000 URLs
- **Feodo**: ~1-2 seconds for 500 IPs
- **PhishTank**: ~30-60 seconds for full feed
- **OTX**: ~10-20 seconds for 50 pulses

## Best Practices

### 1. Feed Selection

- **Always Enable**: URLhaus, Feodo (high quality, no key required)
- **If Phishing is a Concern**: Enable PhishTank
- **For Broader Coverage**: Add AlienVault OTX (requires key)

### 2. Sync Frequency

- **High-Risk Environments**: Every 2-4 hours
- **Standard Environments**: Every 6-12 hours
- **Low-Risk/Lab**: Daily

### 3. Confidence Thresholds

- **Auto-Block**: Confidence ≥ 0.9 (Feodo, abuse.ch)
- **Alert Only**: Confidence 0.7-0.89 (OTX community data)
- **Ignore**: Confidence < 0.7 (noisy sources)

### 4. Data Retention

- **Keep Recent**: Last 30-90 days
- **Archive Old IOCs**: Beyond 90 days, archive to reduce DB size
- **Cleanup Regularly**: Run `cleanup_old_iocs()` weekly

### 5. Attribution

- **Always Credit Sources**: Show which feed flagged the IOC
- **Respect ToS**: All feeds have terms of service
- **Rate Limits**: Don't hammer APIs (use caching/sync intervals)

## Troubleshooting

### No IOCs After Sync

```bash
# Check logs
docker logs ai-service | grep threat_intel

# Verify network access
docker-compose exec ai-service curl -I https://urlhaus-api.abuse.ch/

# Check permissions on data directory
ls -la ./data/
```

### OTX API Errors

- Verify API key is correct
- Check rate limits (free tier: 10,000 requests/hour)
- Ensure network can reach `otx.alienvault.com`

### Slow Lookups

- Verify SQLite indexes exist
- Check database file size (should be <100MB for normal workloads)
- Consider cleanup of old IOCs

### PhishTank Rate Limiting

- Without API key: limited to 1 request every 5 minutes
- With API key: higher limits
- Use caching, sync less frequently

## Advanced Features

### Custom Feeds

Add your own threat intel:

```python
from orion_ai.threat_intel.ioc_models import IOC, IOCType, IntelSource, ThreatType
from orion_ai.threat_intel.store import IOCStore

store = IOCStore(db_path="/data/threat_intel.db")

# Add custom IOCs
custom_iocs = [
    IOC(
        value="evil.internal.network",
        type=IOCType.DOMAIN,
        source=IntelSource.CUSTOM,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        confidence=1.0,
        threat_type=ThreatType.C2,
        tags=["internal", "honeypot"],
        description="Internal honeypot hit"
    )
]

store.add_iocs(custom_iocs)
```

### Match Statistics

Track IOC matches:

```python
# Get recent matches
matches = store.get_recent_matches(limit=100)

for match in matches:
    print(f"{match['matched_at']}: {match['ioc_value']} ({match['ioc_source']})")
```

### Threat Reports

Generate threat intelligence reports:

```python
stats = store.get_stats()

print(f"""
Threat Intelligence Summary
===========================
Total IOCs: {stats['total']}
  - Domains: {stats.get('domain', 0)}
  - IPs: {stats.get('ip', 0)}
  - URLs: {stats.get('url', 0)}

Matches (24h): {stats['matches_24h']}
Total Matches: {stats['total_matches']}
""")
```

## Privacy & Security

- **All Processing is Local**: No data sent to external services except feed updates
- **No Log Retention on Feeds**: We only fetch IOCs, not submit data
- **SQLite Encryption**: Consider encrypting `/data` volume for sensitive environments
- **Access Control**: Restrict access to IOC database
- **Audit Trail**: All TI matches are logged

## Feed Update Schedule

Recommended sync intervals:

| Feed | Update Frequency | Reason |
|------|-----------------|---------|
| URLhaus | Every 4 hours | Active campaigns change rapidly |
| Feodo | Every 4 hours | Botnet infrastructure is dynamic |
| PhishTank | Every 6 hours | Phishing sites have short lifespans |
| OTX | Every 6-12 hours | Community pulses updated regularly |

## Resources

- [abuse.ch](https://abuse.ch) - URLhaus, Feodo, and other feeds
- [AlienVault OTX](https://otx.alienvault.com) - Open Threat Exchange
- [PhishTank](https://www.phishtank.com) - Phishing verification
- [MISP](https://www.misp-project.org) - Open-source threat intel platform (future integration)

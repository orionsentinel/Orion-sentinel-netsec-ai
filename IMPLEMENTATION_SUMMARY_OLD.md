# Orion Sentinel - Complete Implementation Summary

This document summarizes the complete Orion Sentinel NSM + AI system implementation.

## Architecture Overview

**Two-Pi Setup:**
- **Pi #1 (DNS Pi)**: Runs `orion-sentinel-dns-ha` - Pi-hole + Unbound + Keepalived VIP
- **Pi #2 (Security Pi)**: Runs `orion-sentinel-nsm-ai` - This repository

**Pi #2 Components:**
1. **NSM Stack**: Suricata IDS (passive) + Loki + Promtail + Grafana
2. **AI Service**: ML-based threat detection with AI Hat acceleration
3. **Threat Intelligence**: Multi-source IOC feeds + Community digests
4. **Monitoring**: Prometheus + node_exporter + cAdvisor + alerting

---

## What's Been Implemented

### 1. Automatic Lifecycle Management ✅

**No user intervention required - system manages itself:**

#### Phase 1: Data Collection (Days 1-30)
- `data_collector.py` - Collects baseline network behavior
- Stores device features (22 metrics per device per time window)
- Stores domain features (13 lexical/statistical features)
- Compressed JSONL format with daily rotation
- Progress tracking and readiness detection

#### Phase 2: Auto-Training (Day 7+)
- `auto_trainer.py` - Trains models when sufficient data collected
- **Device Anomaly Model**: Isolation Forest (unsupervised)
  - Learns normal device behavior patterns
  - Detects anomalous connection patterns, DNS activity
- **Domain Risk Model**: Random Forest with pseudo-labels
  - Learns benign domain characteristics
  - Scores new domains for DGA/phishing risk
- ONNX export for AI Hat acceleration (3-4x speedup)
- Automatic validation and deployment

#### Phase 3: Detection Mode (Day 7+)
- Automatically switches to production detection
- Runs periodic anomaly detection (configurable interval)
- Emits results to Loki for Grafana visibility
- Pi-hole API enforcement for high-risk domains

**Usage:**
```bash
# Just start - system handles everything
cd stacks/nsm && docker compose up -d
cd stacks/ai && docker compose up -d

# System automatically progresses through:
# - Collecting baseline
# - Training models
# - Running detection
```

---

### 2. NSM Stack (Suricata + Loki + Grafana) ✅

**Configuration:** `stacks/nsm/docker-compose.yml`

#### Suricata IDS
- Passive AF_PACKET capture on mirrored interface
- ARM-optimized (2GB memory limit, tuned ring buffers)
- Writes eve.json to bind-mounted volume
- Configuration: `stacks/nsm/suricata/suricata.yaml`

#### Loki
- Log aggregation with 7-day retention
- Chunk compaction for storage efficiency
- Ingests: Suricata events, AI results, DNS logs, threat intel
- Configuration: `stacks/nsm/loki/loki-config.yaml`

#### Promtail
- Ships logs to Loki with labeled streams
- Monitors: Suricata eve.json, AI output logs
- Labels: `service="suricata"`, `pi="pi2-security"`, etc.
- Configuration: `stacks/nsm/promtail/promtail-config.yml`

#### Grafana
- Pre-provisioned Loki datasource
- Complete dashboard with 6 panels (see below)
- Configuration: `stacks/nsm/grafana/datasources.yml`

---

### 3. AI Service Stack ✅

**Configuration:** `stacks/ai/docker-compose.yml`

#### Python Package (`src/orion_ai/`)

**Core Modules:**
- `config.py` - Pydantic-based configuration from environment
- `log_reader.py` - Loki API client for reading NSM/DNS logs
- `feature_extractor.py` - Transforms logs to numerical features
- `model_runner.py` - ONNX/TFLite inference with AI Hat support
- `pipelines.py` - Device anomaly + domain risk orchestration
- `output_writer.py` - Structured JSON logging to Loki
- `http_server.py` - FastAPI endpoints for manual triggering
- `pihole_client.py` - Pi-hole API client with retry logic

**Data Collection:**
- `data_collector.py` - Baseline data collection (7-30 days)
- `auto_trainer.py` - Automatic model training

**Threat Intelligence:**
- `threat_intel.py` - Original multi-source manager (AlienVault OTX, URLhaus, Feodo, PhishTank)
- `threat_intel/ioc_models.py` - IOC, Advisory, IntelMatch data models
- `threat_intel/sources.py` - RSS and JSON API source implementations
- `threat_intel/ioc_extractor.py` - Regex-based IOC extraction with defanging
- `threat_intel/store.py` - SQLite storage with fast lookups
- `threat_intel/community_sources.py` - Reddit, security blogs (RSS)
- `threat_intel/community_digest.py` - Human-readable digest generation

**Entry Point:**
- `main.py` - Multiple modes: collect, batch, api, oneshot

#### Execution Modes

```bash
# Collect mode (automatic during first 7-30 days)
python main.py --mode collect

# Batch mode (periodic detection - default after training)
python main.py --mode batch --interval 15

# API mode (on-demand via HTTP)
python main.py --mode api --port 8080

# Oneshot mode (manual run)
python main.py --mode oneshot --start "last 1h"
```

---

### 4. Threat Intelligence System ✅

#### Machine-Readable IOC Feeds

**Sources Integrated:**
1. **AlienVault OTX** - Comprehensive threat intelligence (API)
2. **URLhaus** (abuse.ch) - Malicious URLs/domains (JSON API)
3. **Feodo Tracker** (abuse.ch) - Botnet C2 IPs (JSON API)
4. **PhishTank** - Verified phishing sites (JSON API)

**Features:**
- Async feed fetching (parallel downloads)
- SQLite cache with sub-millisecond lookups
- Automatic deduplication
- 90-day retention with cleanup
- Source attribution and confidence tracking
- IOC types: IP, Domain, URL, Hashes (MD5/SHA1/SHA256), CVE

**Data Flow:**
```
Fetch feeds → Extract IOCs → Store in SQLite → 
Cross-reference with logs → Emit intel_match events to Loki
```

#### Community Intelligence (Human Context)

**Sources Integrated:**
1. **Reddit** - r/netsec, r/threatintel, r/cybersecurity (RSS/API)
2. **Schneier on Security** - Bruce Schneier's blog (RSS)
3. **Cisco Talos** - Threat research blog (RSS)
4. **SANS ISC** - Internet Storm Center (RSS)
5. **Krebs on Security** - Brian Krebs blog (RSS)
6. **Bleeping Computer** - Security news (RSS)
7. **Threatpost** - Threat intelligence news (RSS)

**Features:**
- Keyword filtering for threat-relevant posts
- IOC extraction from posts (LOW confidence for investigation)
- Markdown digest generation with trending topics
- Top discussions summary
- Digest events in Loki stream: `community_intel_digest`

**Example Digest Output:**
```markdown
# Security Community Intelligence Digest (24h)
**Posts Analyzed:** 47

## Trending Topics
- **ransomware**: 12 mentions
- **apt**: 8 mentions
- **zero-day**: 6 mentions

## Notable Discussions
### 1. New Ransomware Variant Targeting Healthcare
**Source:** r/netsec
**URL:** https://reddit.com/...
> [Post preview...]
```

---

### 5. Grafana Dashboard ✅

**File:** `stacks/nsm/grafana/dashboards/orion-sentinel-nsm.json`

**6 Panels:**

1. **Suricata Alerts by Severity** (Time Series)
   - Query: `sum by (severity) (count_over_time({service="suricata", event_type="alert"} [$__interval]))`
   - Stacked view with color coding: Red (High), Orange (Medium), Yellow (Low)
   
2. **Top 10 Alert Signatures** (Pie Chart)
   - Query: `topk(10, sum by (signature) (count_over_time({service="suricata", event_type="alert"} [24h])))`
   - Shows most common attack patterns

3. **AI Device Anomalies** (Table)
   - Query: `{service="ai-device-anomaly"} | json`
   - Columns: Device IP, Anomaly Score (gauge), Window Start/End
   - Sortable by anomaly score
   - Last 50 anomalies

4. **Threat Intel Matches** (Table)
   - Query: `{stream="intel_match"} | json`
   - Columns: IOC Value, Type (with icons), Source, Device IP, Confidence
   - VirusTotal links for IOCs
   - Last 50 matches

5. **AI Domain Risk Scores** (Table)
   - Query: `{service="ai-domain-risk"} | json`
   - Columns: Domain, Risk Score (gauge), Action (BLOCK/ALLOW with icons)
   - URLhaus links for domains
   - Last 50 domains

6. **Community Intelligence Digest** (Table)
   - Query: `{stream="community_intel_digest"} | json`
   - Shows: Time range, post count, sources, trending keywords, summary
   - Latest 5 digests

**Dashboard Features:**
- Auto-refresh every 30 seconds
- Time range selector (default: 24h)
- Dark theme optimized
- Responsive layout
- External integration links

---

### 6. Prometheus Monitoring ✅

#### Recording Rules (`stacks/nsm/prometheus/rules/`)

**DNS Traffic Rules:**
- `instance:dns_queries_total:rate5m` - Total queries per instance
- `instance:dns_queries_blocked:rate5m` - Blocked queries per instance
- `instance:dns_block_rate:ratio` - Block rate percentage
- `client:dns_queries_total:rate5m` - Per-client query rates
- `client:dns_block_rate:ratio` - Per-client block rates
- `cluster:*` - Cluster-wide aggregations
- `topk:*` - Top 10 clients and blocked clients

**Benefits:**
- Pre-aggregated metrics for fast Grafana queries
- Reduced query load on Prometheus
- Consistent metric naming
- 5-minute rate windows for smoothing

#### Alerting Rules

**DNS Health Alerts (`dns-alerts.yml`):**
- **DNSLowBlockRate** - <1% for 15m (bypass detection)
- **DNSNoTraffic** - <0.1 qps for 10m (service down)
- **PiHoleExporterDown** - Exporter unreachable 5m
- **UnboundExporterDown** - Unbound metrics unavailable
- **DNSQuerySpike** - 3x normal traffic (DDoS/tunneling)
- **DNSHighClientBlockRate** - >70% blocked (malware)
- **PiHoleServiceUnhealthy** - Pi-hole reports unhealthy

**System Resource Alerts (`system-alerts.yml`):**
- **HighCpuUsage** - Load >80% for 10m
- **HighCpuUtilization** - CPU time >80% for 10m
- **HighMemoryUsage** - <15% RAM available for 5m
- **HighFsUsage** - <15% disk space (85% used)
- **CriticalFsUsage** - <5% disk space (emergency)

**Docker Health Alerts (`system-alerts.yml`):**
- **DockerContainerDown** - cAdvisor unreachable
- **ContainerHighMemory** - >90% of memory limit
- **ContainerFrequentRestarts** - Crash loop detection
- **CriticalContainerMissing** - Essential services down
- **ContainerHighCpu** - >80% CPU for 10m

**Alert Features:**
- Severity: warning/critical
- Detailed root cause descriptions
- Remediation guidance
- Runbook URLs
- Context-rich labels
- Human-readable values
- Raspberry Pi 5 tuned

---

## Configuration Files

### Environment Variables

**NSM Stack (`.env.example`):**
```bash
NSM_IFACE=eth1                    # Mirrored traffic interface
LOKI_RETENTION_PERIOD=168h        # 7 days
GRAFANA_ADMIN_PASSWORD=changeme
```

**AI Service (`.env.example`):**
```bash
# Loki
LOKI_URL=http://loki:3100

# Models
DEVICE_ANOMALY_MODEL=/models/device_anomaly.onnx
DOMAIN_RISK_MODEL=/models/domain_risk.onnx

# Detection thresholds
DEVICE_ANOMALY_THRESHOLD=0.7
DOMAIN_RISK_THRESHOLD=0.8

# Pi-hole enforcement
PIHOLE_API_URL=http://pi1-dns/admin/api.php
PIHOLE_API_TOKEN=your-token-here
PIHOLE_ENFORCE_BLOCKS=true

# Threat Intel
THREAT_INTEL_ENABLE=true
THREAT_INTEL_OTX_API_KEY=optional-but-recommended
THREAT_INTEL_REFRESH_HOURS=6

# Community Intel
REDDIT_CLIENT_ID=optional
REDDIT_CLIENT_SECRET=optional
```

---

## Documentation

**Complete documentation in `docs/`:**

1. **architecture.md** - System architecture, data flows, component specs
2. **pi2-setup.md** - Raspberry Pi 5 setup, Docker install, port mirroring
3. **logging-and-dashboards.md** - Loki queries, Grafana usage
4. **ai-stack.md** - AI design, model specs, feature definitions
5. **integration-orion-dns-ha.md** - DNS log shipping, Pi-hole API usage
6. **ai-hat-setup.md** - AI Hat installation, model training workflow

**Quick start guides:**
- **QUICKSTART.md** - Fast deployment reference
- **CONTRIBUTING.md** - Development guidelines

---

## Deployment

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/yorgosroussakis/Orion-sentinel-netsec-ai.git
cd Orion-sentinel-netsec-ai

# 2. Configure NSM stack
cd stacks/nsm
cp .env.example .env
# Edit .env: Set NSM_IFACE to your mirrored interface (e.g., eth1)

# 3. Deploy NSM stack
docker compose up -d

# 4. Configure AI service
cd ../ai
cp .env.example .env
# Edit .env: Configure Loki URL, Pi-hole API, threat intel keys

# 5. Deploy AI service (starts in collection mode automatically)
docker compose up -d
```

### System will automatically:
1. Days 1-7: Collect baseline data
2. Day 7+: Train models when sufficient data collected
3. Day 7+: Switch to detection mode
4. Ongoing: Run threat detection and enforcement

### Monitoring

```bash
# Check logs
docker compose logs -f

# Access Grafana
open http://pi2-ip:3000
# Default credentials: admin/admin (change on first login)

# Access Loki
open http://pi2-ip:3100

# Trigger manual detection (API mode)
curl -X POST "http://pi2-ip:8080/api/v1/detect/device?minutes_ago=10"
```

---

## Integration with orion-sentinel-dns-ha

**Pi #1 → Pi #2 Communication:**

1. **DNS Log Shipping:**
   - Pi #1 runs Promtail to ship Pi-hole/Unbound logs
   - Target: `http://pi2-ip:3100/loki/api/v1/push`
   - Labels: `service="pihole"`, `pi="pi1-dns"`

2. **Pi-hole API Enforcement:**
   - Pi #2 AI service calls Pi #1 Pi-hole API
   - Endpoint: `http://pi1-ip/admin/api.php`
   - Actions: Add/remove domains to blocklist
   - Authentication: API token in `.env`

**Network Requirements:**
- Pi #2 allows port 3100 from Pi #1 (Loki ingestion)
- Pi #1 allows port 80 from Pi #2 (API calls)
- Both Pis on same network or routable

---

## Security Considerations

1. **Passive Monitoring Only:**
   - Pi #2 never inline in traffic path
   - No IPS functionality - detection only
   - Enforcement via Pi-hole API (DNS layer)

2. **Data Privacy:**
   - All logs stored locally on Pi #2
   - No external transmission of network data
   - Threat intel feeds are public sources

3. **API Security:**
   - Pi-hole API requires authentication token
   - Grafana admin password must be changed
   - Loki has no authentication (internal network only)

4. **Resource Limits:**
   - All containers have memory limits
   - Prevents OOM on Raspberry Pi 5
   - See docker-compose.yml for specifics

---

## Performance Tuning

**Raspberry Pi 5 Optimizations:**

1. **Suricata:**
   - 2GB memory limit
   - Reduced ring buffer sizes
   - AF_PACKET capture mode
   - Minimal rule loading initially

2. **Loki:**
   - 7-day retention (configurable)
   - Chunk compaction enabled
   - Filesystem storage

3. **AI Service:**
   - AI Hat acceleration (3-4x speedup)
   - Batch processing to reduce overhead
   - Configurable detection intervals

4. **Prometheus:**
   - Recording rules reduce query load
   - 5-minute rate windows
   - Efficient aggregations

---

## Troubleshooting

**No traffic in Suricata:**
1. Check interface: `ip link show`
2. Verify port mirroring on switch/router
3. Check Suricata logs: `docker logs suricata`

**Models not training:**
1. Check collection stats: View data_collector logs
2. Ensure 7+ days of data
3. Check disk space for training data

**High memory usage:**
1. Reduce Loki retention
2. Lower Suricata ring buffers
3. Reduce AI batch size

**No threat intel matches:**
1. Verify feeds are fetching: Check threat_intel logs
2. Check SQLite database: `/data/threat_intel/ioc_store.db`
3. Ensure correlation is running

---

## Next Steps

**Recommended enhancements:**

1. **Add more threat intel sources:**
   - MISP integration
   - Custom feed sources
   - Emerging Threats rules

2. **Enhance AI models:**
   - Retrain monthly with updated baseline
   - Add supervised training with labeled malicious samples
   - Fine-tune thresholds based on false positive rates

3. **Expand monitoring:**
   - Add Zeek for protocol analysis
   - Network flow analysis (NetFlow/IPFIX)
   - File extraction and analysis

4. **Improve dashboards:**
   - Add DNS-specific Grafana dashboard
   - System resource dashboard
   - Docker container dashboard
   - AI performance metrics dashboard

5. **Automation:**
   - Automatic monthly model retraining
   - Threat feed auto-refresh
   - Automated reporting

---

## Support and Documentation

**For issues:**
- GitHub Issues: https://github.com/yorgosroussakis/Orion-sentinel-netsec-ai/issues
- Documentation: `docs/` directory
- Runbooks: Referenced in alert annotations

**Key files:**
- System architecture: `docs/architecture.md`
- Setup guide: `docs/pi2-setup.md`
- AI training: `docs/ai-hat-setup.md`
- DNS integration: `docs/integration-orion-dns-ha.md`

---

## License

See LICENSE file in repository root.

---

**Version:** 1.0.0  
**Last Updated:** 2025-11-19  
**Author:** Orion Sentinel Team

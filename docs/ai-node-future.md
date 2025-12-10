# Future AI Node Architecture

This document describes the planned architecture for a dedicated **AI Node** in the Orion Sentinel ecosystem. This node is **NOT required** for the base Network Security Monitoring (NSM) deployment and is documented here for future implementation.

---

## Status: Future Enhancement

**Current Status:** Documentation only  
**Implementation:** Planned for v2.0+  
**Required for base NSM:** ❌ No

---

## Purpose and Scope

### What the AI Node Will Do

The AI Node is a **separate Raspberry Pi 5 with an AI HAT** (e.g., Hailo-8L) that provides:

1. **AI-Powered Threat Detection**
   - Anomaly detection on network behavior
   - Domain risk scoring (DGA detection, phishing)
   - Device behavioral analysis
   - Protocol anomaly detection

2. **Event Enrichment**
   - Add risk scores to raw events
   - Provide human-readable explanations
   - Context from threat intelligence
   - MITRE ATT&CK mapping

3. **Advanced Correlation**
   - Multi-source event correlation
   - Attack chain reconstruction
   - False positive reduction
   - Behavioral baselining

### What the AI Node Will NOT Do

- **Not required for packet capture** - NetSec Pi handles all Suricata IDS
- **Not a replacement for signature-based detection** - Complements Suricata
- **Not a log aggregator** - CoreSrv Loki remains the central log store
- **Not required for basic NSM** - NetSec stack works without it

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CoreSrv Node                                │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Loki (Central Log Aggregation)                                │ │
│  │  • Receives logs from NetSec Pi                                │ │
│  │  • Receives enriched events from AI Node                       │ │
│  │  • Exposes query API for AI Node                               │ │
│  └──────────────┬───────────────────────────┬─────────────────────┘ │
└─────────────────┼───────────────────────────┼───────────────────────┘
                  │                           │
                  │ Query logs                │ Push enriched events
                  ▼                           ▲
┌─────────────────────────────────────────────┴───────────────────────┐
│                       AI Node (Pi 5 + AI HAT)                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  AI Detection Services                                         │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  1. Event Reader Service                                 │ │ │
│  │  │     • Queries Loki for new Suricata events               │ │ │
│  │  │     • Filters by event types (alerts, flows, DNS)        │ │ │
│  │  │     • Maintains cursor for incremental reads             │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  2. Feature Extraction Service                           │ │ │
│  │  │     • Builds feature vectors from raw events             │ │ │
│  │  │     • Aggregates per-device statistics                   │ │ │
│  │  │     • Temporal feature engineering                       │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  3. AI Inference Engine                                  │ │ │
│  │  │     • Device anomaly detection model (ONNX)              │ │ │
│  │  │     • Domain risk scoring model (ONNX/TFLite)            │ │ │
│  │  │     • Runs on AI HAT (Hailo-8L) for acceleration         │ │ │
│  │  │     • Fallback to CPU if AI HAT not available            │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  4. Enrichment Service                                   │ │ │
│  │  │     • Adds risk scores to events                         │ │ │
│  │  │     • Generates human-readable explanations              │ │ │
│  │  │     • Cross-references threat intelligence               │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  5. Event Publisher Service                              │ │ │
│  │  │     • Writes enriched SecurityEvents to Loki             │ │ │
│  │  │     • Optionally publishes to HTTP API/webhook           │ │ │
│  │  │     • Maintains audit log of AI decisions                │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                  │
                  │ Read Suricata events
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       NetSec Pi (Sensor Node)                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Suricata IDS → Promtail → Loki (on CoreSrv)                  │ │
│  │  (Continues operating independently of AI Node)               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow (Conceptual)

### Step 1: NetSec Pi Generates Events

NetSec Pi (Suricata) generates raw security events and ships them to CoreSrv Loki:

```json
{
  "timestamp": "2024-12-10T09:00:00.000Z",
  "event_type": "alert",
  "src_ip": "192.168.1.50",
  "dest_ip": "203.0.113.5",
  "alert": {
    "signature": "ET MALWARE Suspicious DNS Query",
    "severity": 2,
    "category": "Potential Corporate Privacy Violation"
  }
}
```

### Step 2: AI Node Reads Events from Loki

The AI Node queries Loki for new events (incremental read):

```bash
# Example Loki query (LogQL)
{orion_node_role="netsec", app="suricata"} 
  | json 
  | event_type="alert" 
  | __timestamp__ > ${last_processed_timestamp}
```

### Step 3: AI Node Performs Inference

Feature extraction + model inference:

```python
# Pseudocode
features = extract_features(event)
# features: [src_ip_entropy, dest_port_rarity, dns_qname_length, ...]

risk_score = model.predict(features)
# risk_score: 0.0 - 1.0 (0 = benign, 1 = malicious)

explanation = generate_explanation(features, risk_score)
# explanation: "High risk: Destination IP is known C2, unusual DNS query pattern"
```

### Step 4: AI Node Publishes Enriched Event

Writes enriched SecurityEvent back to Loki:

```json
{
  "timestamp": "2024-12-10T09:00:05.000Z",
  "event_type": "security_event",
  "source": "ai-node",
  "original_event_id": "suricata-alert-12345",
  "risk_score": 0.92,
  "confidence": 0.85,
  "explanation": "High-risk domain (DGA-like), destination IP on threat intel list",
  "mitre_attack": ["T1071.004"],  # DNS tunneling
  "recommended_action": "block_domain",
  "enrichments": {
    "threat_intel_match": true,
    "threat_intel_source": "AlienVault OTX",
    "device_baseline_deviation": 3.2
  },
  "original_event": { /* original Suricata alert */ }
}
```

### Step 5: CoreSrv Grafana Displays Enriched Events

Grafana dashboards query both:
- **Raw Suricata alerts** (immediate visibility)
- **AI-enriched events** (risk scores, explanations)

Users can:
- Filter by risk_score >= 0.8
- See AI explanations alongside raw alerts
- Track AI model accuracy over time

---

## Hardware Requirements

### Minimum Specs

- **Raspberry Pi 5** (4GB RAM minimum, 8GB recommended)
- **AI HAT** (e.g., Hailo-8L with ~13 TOPS)
- **MicroSD or USB Storage** (64GB minimum, 128GB recommended)
- **Network**: Gigabit Ethernet connection to CoreSrv LAN

### No NVMe Required

Unlike the NetSec Pi, the AI Node does NOT need NVMe:
- Reads events from Loki (no local log storage)
- Writes enriched events back to Loki (no heavy disk I/O)
- Model files are small (< 1 GB)
- No packet captures or PCAP storage

### AI HAT Options

| HAT Model | Performance | Cost | Power | Notes |
|-----------|-------------|------|-------|-------|
| **Hailo-8L** (official) | ~13 TOPS | ~$70 | 2-3W | Best compatibility, recommended |
| Google Coral M.2 | ~4 TOPS | ~$50 | 2W | Requires M.2 adapter |
| Intel Neural Compute Stick | ~1 TOPS | ~$80 | USB | Deprecated, not recommended |

**Fallback:** CPU-only inference works but is slower (acceptable for home networks).

---

## Integration Points

### Environment Variables

Future `.env` variables for AI Node integration:

```bash
# AI Node Configuration (NetSec Pi .env)
# These will be documented but NOT required for base deployment

# Enable AI enrichment (optional)
ORION_AI_ENABLED=false  # Default: disabled

# AI Node API endpoint (if AI Node exposes HTTP API)
ORION_AI_GATEWAY_URL=http://192.168.x.x:8080

# AI Node authentication (optional)
ORION_AI_API_KEY=

# Controls whether NetSec waits for AI enrichment before shipping logs
ORION_AI_INLINE_ENRICHMENT=false  # Default: async (don't wait)
```

### API Endpoints (Future)

**AI Node exposes (optional):**

- `POST /enrich` - Enrich a single event
- `GET /health` - AI Node health status
- `GET /models` - List loaded models and versions
- `GET /stats` - Inference statistics (avg latency, throughput)

**NetSec Pi does NOT call these** - AI Node pulls from Loki instead.

### Loki Label Conventions

**Raw Suricata events (from NetSec Pi):**
```
{
  orion_node_role="netsec",
  orion_node_name="netsec-pi-01",
  app="suricata",
  stream="eve-json"
}
```

**AI-enriched events (from AI Node):**
```
{
  orion_node_role="ai",
  orion_node_name="ai-pi-01",
  app="orion-ai",
  stream="security-events",
  source_node="netsec-pi-01"  # Original event source
}
```

This allows Grafana to query both raw and enriched events separately or together.

---

## Failure Modes and Resilience

### What Happens if AI Node is Offline?

**NetSec Pi continues operating normally:**
- Suricata keeps capturing and analyzing traffic
- Promtail keeps shipping logs to Loki
- Grafana shows raw Suricata alerts (no AI scores)
- No errors or degradation of base NSM functionality

**CoreSrv Grafana:**
- Shows message: "AI enrichment unavailable"
- Dashboards still display raw alerts and flows
- Users can manually review events

### What Happens if AI Node Lags Behind?

If AI Node cannot keep up with event volume:
- **Queues events internally** (up to max buffer size)
- **Skips enrichment for low-priority events** (flows, DNS)
- **Prioritizes high-severity alerts** for enrichment
- **Logs backlog metrics** to Prometheus for monitoring

CoreSrv Prometheus alert:
```promql
ai_node_event_backlog > 10000
```

### What Happens if AI Model Fails?

If model inference fails (corrupted model, OOM, etc.):
- **Logs error to Loki** with details
- **Publishes event without enrichment** (risk_score = null)
- **Falls back to CPU inference** if AI HAT fails
- **Alerts ops team** via Prometheus/Alertmanager

---

## Model Development and Deployment

### Model Training (Out of Scope for v1)

Training pipeline (future):
1. Collect labeled dataset from Loki (weeks/months of traffic)
2. Extract features from raw events
3. Train models using Jupyter notebooks or cloud GPUs
4. Export to ONNX/TFLite for edge inference
5. Validate on holdout dataset
6. Deploy to AI Node

### Model Deployment

Future process:
1. Upload model files to AI Node (via SCP or API)
2. AI Node validates model format and signatures
3. Model loaded into inference engine
4. Warm-up run on test data
5. Switch to new model (A/B testing)
6. Monitor inference latency and accuracy

### Model Versions

Recommended model versioning:
```
/models/
  device-anomaly-v1.0.onnx
  device-anomaly-v1.1.onnx  # Latest
  domain-risk-v2.0.tflite
  domain-risk-v2.1.tflite   # Latest
```

AI Node config:
```yaml
models:
  device_anomaly:
    path: /models/device-anomaly-v1.1.onnx
    engine: onnx
    accelerator: hailo  # or cpu
  domain_risk:
    path: /models/domain-risk-v2.1.tflite
    engine: tflite
    accelerator: hailo
```

---

## Performance Expectations

### Inference Latency

| Model | Hardware | Latency (avg) | Throughput |
|-------|----------|---------------|------------|
| Device Anomaly | Hailo-8L | 5-10 ms | 100-200 events/sec |
| Device Anomaly | CPU (Pi 5) | 50-100 ms | 10-20 events/sec |
| Domain Risk | Hailo-8L | 2-5 ms | 200-400 events/sec |
| Domain Risk | CPU (Pi 5) | 20-50 ms | 20-50 events/sec |

### Event Volume Estimates

Typical home network (100 Mbps, 20 devices):
- **Suricata alerts:** 10-100 per hour
- **DNS queries:** 1,000-10,000 per hour
- **Flows:** 10,000-100,000 per hour

**AI Node can easily handle this volume** even on CPU-only.

Enterprise/high-traffic networks (1 Gbps, 100+ devices):
- **Suricata alerts:** 100-1,000 per hour
- **DNS queries:** 100,000+ per hour
- **Flows:** 1,000,000+ per hour

**AI HAT required** for real-time enrichment at this scale.

---

## Security Considerations

### AI Node Security

**Network Isolation:**
- AI Node should only communicate with CoreSrv (Loki)
- No direct internet access required (models pre-loaded)
- Optional: VPN for model updates from external repos

**Container Security:**
- Run AI services as non-root
- Use read-only filesystems where possible
- Mount model files read-only
- Drop unnecessary capabilities

**Data Privacy:**
- All inference happens locally (no cloud APIs)
- No telemetry or model updates without approval
- Event data never leaves on-premises network

### Model Integrity

Future improvements:
- Model signing with GPG keys
- Checksum verification on load
- Audit log of model changes
- RBAC for model deployment

---

## Migration Path from Current Architecture

### Phase 1: Current State (v1.0)

**What exists today:**
- NetSec Pi with Suricata + Promtail
- CoreSrv with Loki + Grafana
- AI services running ON NetSec Pi (not dedicated AI Node)

**Characteristics:**
- Single-node deployment (NetSec Pi does NSM + AI)
- AI services run in Docker containers alongside Suricata
- Works well for low-traffic networks

### Phase 2: Transition (v1.5 - Optional)

**Changes:**
- AI services remain on NetSec Pi
- Add `ORION_AI_ENABLED` flag to `.env`
- Refactor AI services to read from Loki (instead of direct file access)
- Prepare for future offloading to dedicated AI Node

**Benefits:**
- No new hardware required
- Tests AI Node data flow patterns
- Easy rollback to v1.0

### Phase 3: Dedicated AI Node (v2.0)

**Changes:**
- Deploy new Pi 5 with AI HAT
- Move AI services from NetSec Pi to AI Node
- NetSec Pi becomes pure sensor (Suricata + Promtail only)
- AI Node pulls events from CoreSrv Loki

**Benefits:**
- NetSec Pi has more resources for Suricata
- AI Node can use hardware acceleration
- Easier to scale (add more AI Nodes if needed)
- Clearer separation of concerns

---

## Cost Analysis

### AI Node Hardware Cost

| Component | Cost (USD) | Notes |
|-----------|------------|-------|
| Raspberry Pi 5 (8GB) | $80 | Official pricing |
| Hailo-8L AI HAT | $70 | Official AI HAT |
| MicroSD card (128GB) | $15 | Class 10 A2 |
| Power supply (5V 5A) | $15 | Official or equivalent |
| Case with cooling | $20 | Passive or active cooling |
| **Total** | **$200** | One-time investment |

### Operational Cost

- **Power consumption:** ~10W average (AI HAT idle) → ~$12/year at $0.15/kWh
- **Maintenance:** Minimal (same as NetSec Pi)
- **Model updates:** Free (open-source models or self-trained)

### Cost-Benefit

**Benefits:**
- Reduced false positives (fewer alerts to review)
- Faster threat detection (anomaly detection vs. signatures)
- Context-rich alerts (explanations, not just signatures)
- Continuous learning (models improve over time)

**Not Worth It If:**
- Network is very small (< 5 devices)
- No dedicated ops team to review AI insights
- Budget-constrained (stick with Suricata-only)

---

## Non-Goals for v1.0

The following are **explicitly out of scope** for the base NetSec deployment:

❌ **No AI Node required** - Base NSM works without it  
❌ **No AI HAT required** - NetSec Pi uses standard Pi 5  
❌ **No model training** - Pre-trained models will be provided later  
❌ **No inline AI enrichment** - AI Node pulls from Loki asynchronously  
❌ **No AI-based blocking** - SOAR playbooks handle automated response  
❌ **No real-time dashboards for AI** - CoreSrv Grafana shows raw alerts first  

---

## Future Enhancements (Post v2.0)

- **Multi-model ensemble** (combine multiple AI models for better accuracy)
- **Online learning** (models retrain on new data periodically)
- **Federated learning** (share insights across multiple Orion deployments without sharing raw data)
- **Explainable AI dashboards** (visualize model decisions and feature importance)
- **A/B testing framework** (compare model versions in production)
- **Model drift detection** (alert when model performance degrades)

---

## Summary

The **AI Node** is a planned future enhancement to the Orion Sentinel ecosystem:

✅ **Optional** - Not required for base NSM  
✅ **Separate hardware** - Dedicated Pi 5 with AI HAT  
✅ **Async architecture** - NetSec Pi operates independently  
✅ **Loki-centric** - Reads from and writes to CoreSrv Loki  
✅ **Graceful degradation** - System works fine if AI Node is offline  
✅ **Documented now** - Architecture planned, implementation later  

For current deployment, focus on NetSec Pi + CoreSrv integration.  
AI Node can be added later when ready.

---

**Questions or feedback?** Open an issue in the GitHub repo.

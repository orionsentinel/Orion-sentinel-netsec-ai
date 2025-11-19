# AI Stack

This document describes the AI-powered threat detection service in the Orion Sentinel NSM + AI system.

## Overview

The AI service runs on Raspberry Pi 5 with the AI Hat (~13 TOPS) to provide:
1. **Device Anomaly Detection**: Identifies unusual behavior patterns for individual devices on the network
2. **Domain Risk Scoring**: Detects suspicious domains (DGA, phishing, C2) in DNS traffic

Both pipelines use machine learning models (ONNX or TFLite format) optimized for edge inference.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      AI Service Container                     │
│                                                               │
│  ┌────────────┐       ┌──────────────┐      ┌─────────────┐ │
│  │   Loki     │──────▶│ Log Reader   │─────▶│  Feature    │ │
│  │  (Query)   │       │              │      │  Extractor  │ │
│  └────────────┘       └──────────────┘      └──────┬──────┘ │
│                                                     │         │
│                                                     ▼         │
│                       ┌─────────────────────────────────┐    │
│                       │      Model Runner             │    │
│                       │  - Device Anomaly Model       │    │
│                       │  - Domain Risk Model          │    │
│                       │  - AI Hat Acceleration        │    │
│                       └──────────────┬──────────────────┘    │
│                                      │                        │
│                                      ▼                        │
│  ┌────────────┐       ┌──────────────┐      ┌─────────────┐ │
│  │   Loki     │◀──────│   Output     │◀─────│  Pipelines  │ │
│  │  (Write)   │       │   Writer     │      │             │ │
│  └────────────┘       └──────────────┘      └─────────────┘ │
│                                                     │         │
│                                                     ▼         │
│                                          ┌─────────────────┐ │
│                                          │  Pi-hole Client │ │
│                                          │  (Block Domain) │ │
│                                          └─────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Detection Pipelines

### 1. Device Anomaly Detection

**Purpose**: Identify devices exhibiting unusual network behavior that may indicate:
- Malware infection (C2 beaconing, scanning)
- Compromised device (data exfiltration)
- Insider threat
- Misconfigured device

**Process**:

1. **Data Collection** (per device, per time window):
   - Time window: 5-15 minutes (configurable)
   - Source: Suricata flow and DNS events from Loki
   - Group by: Source IP address

2. **Feature Extraction** (20-30 features):
   ```python
   {
     # Connection features
     "connection_count_in": int,      # Inbound connections
     "connection_count_out": int,     # Outbound connections
     "bytes_sent": int,
     "bytes_received": int,
     "unique_dest_ips": int,
     "unique_dest_ports": int,
     "protocol_tcp_ratio": float,     # % TCP vs UDP
     
     # DNS features
     "dns_query_count": int,
     "unique_domains": int,
     "avg_domain_length": float,
     "avg_domain_entropy": float,
     "nxdomain_ratio": float,         # Failed DNS lookups
     
     # Timing features
     "avg_connection_duration": float,
     "connection_rate_per_minute": float,
     
     # Port patterns
     "common_port_ratio": float,      # % connections to ports 80/443
     "rare_port_count": int,          # Connections to unusual ports
     
     # Data transfer patterns
     "avg_bytes_per_connection": float,
     "upload_download_ratio": float,
   }
   ```

3. **Model Inference**:
   - Model type: Autoencoder or Isolation Forest
   - Input: Feature vector (normalized)
   - Output: Anomaly score (0.0 - 1.0)
     - 0.0 = Normal behavior
     - 1.0 = Highly anomalous

4. **Threshold**:
   - Default: 0.7 (configurable via `DEVICE_ANOMALY_THRESHOLD`)
   - Scores >= threshold → logged as `severity="warning"`
   - Scores >= 0.9 → `severity="critical"`

5. **Output**:
   ```json
   {
     "timestamp": "2024-01-15T10:35:00Z",
     "service": "ai-device-anomaly",
     "severity": "warning",
     "device_ip": "192.168.1.50",
     "device_mac": "aa:bb:cc:dd:ee:ff",  # If available
     "window_start": "2024-01-15T10:25:00Z",
     "window_end": "2024-01-15T10:35:00Z",
     "anomaly_score": 0.87,
     "features": { /* all computed features */ },
     "top_anomalies": [
       "high unique_dest_ips (45, normal: ~5-10)",
       "high nxdomain_ratio (0.3, normal: <0.05)"
     ]
   }
   ```

### 2. Domain Risk Scoring

**Purpose**: Identify malicious or suspicious domains in DNS traffic:
- DGA (Domain Generation Algorithm) domains (malware C2)
- Phishing domains
- Newly registered domains
- Typosquatting

**Process**:

1. **Data Collection**:
   - Time window: Same as device detection or hourly batch
   - Source: DNS queries from Suricata and Pi-hole logs
   - Extract: Unique domains queried

2. **Feature Extraction** (per domain):
   ```python
   {
     # Length features
     "domain_length": int,
     "subdomain_count": int,
     "tld_length": int,
     
     # Character features
     "char_entropy": float,           # Shannon entropy
     "vowel_ratio": float,
     "consonant_ratio": float,
     "digit_ratio": float,
     "special_char_count": int,       # Hyphens, underscores
     
     # Pattern features
     "has_ip_pattern": bool,          # Contains IP-like string
     "max_consonant_streak": int,
     "hex_ratio": float,              # Hex chars / total chars
     
     # TLD features
     "tld_category": str,             # common, rare, suspicious
     "tld_popularity_rank": int,      # Based on public lists
     
     # External features (optional)
     "whois_age_days": int,           # If available
     "alexa_rank": int,               # If available
   }
   ```

3. **Model Inference**:
   - Model type: Binary classifier (DGA/malicious vs benign)
   - Input: Feature vector (normalized)
   - Output: Risk score (0.0 - 1.0)
     - 0.0 = Benign
     - 1.0 = Highly suspicious

4. **Threshold & Policy**:
   - Default: 0.85 (configurable via `DOMAIN_RISK_THRESHOLD`)
   - Scores >= threshold → `action="BLOCK"`
   - Scores < threshold → `action="ALLOW"`

5. **Enforcement**:
   - If `action="BLOCK"`:
     - Call Pi-hole API to add domain to blocklist
     - Log enforcement action

6. **Output**:
   ```json
   {
     "timestamp": "2024-01-15T10:35:00Z",
     "service": "ai-domain-risk",
     "severity": "critical",
     "domain": "xn--c1yn36f.xyz",
     "risk_score": 0.92,
     "action": "BLOCK",
     "features": {
       "domain_length": 14,
       "char_entropy": 3.2,
       "tld": "xyz",
       "tld_category": "rare",
       "hex_ratio": 0.7
     },
     "reason": "High entropy, rare TLD, DGA-like pattern",
     "pihole_response": "success"
   }
   ```

---

## Model Formats and Requirements

### Supported Formats

1. **ONNX** (Open Neural Network Exchange)
   - Recommended for flexibility
   - Supports most frameworks (PyTorch, TensorFlow, scikit-learn)
   - Runtime: `onnxruntime` with ARM optimization

2. **TFLite** (TensorFlow Lite)
   - Optimized for edge devices
   - Smaller file size, faster inference
   - Requires TensorFlow models

### Model Specifications

#### Device Anomaly Model

- **Type**: Autoencoder or Isolation Forest
- **Input Shape**: `(batch_size, num_features)` where `num_features` ≈ 20-30
- **Output Shape**: `(batch_size, 1)` - anomaly score per device
- **Training Data**: Historical network flow + DNS logs labeled by normal behavior
- **Performance**: ~5-10 ms inference time per batch (100 devices) on AI Hat

#### Domain Risk Model

- **Type**: Binary classifier (Random Forest, XGBoost, or Neural Network)
- **Input Shape**: `(batch_size, num_features)` where `num_features` ≈ 15-20
- **Output Shape**: `(batch_size, 1)` - risk score per domain
- **Training Data**: Labeled dataset of benign domains + DGA/phishing domains
  - Benign: Alexa Top 1M, Cisco Umbrella
  - Malicious: DGArchive, PhishTank, URLhaus
- **Performance**: ~1-2 ms inference time per batch (1000 domains) on AI Hat

### Model Training (Out of Scope)

**Note**: This repository does not include model training code. Models should be trained separately.

**Recommended Approach**:
1. Collect baseline network/DNS data from your network (1-2 weeks)
2. Label normal behavior (device anomaly) or use public datasets (domain risk)
3. Train models using scikit-learn, PyTorch, or TensorFlow
4. Export to ONNX or TFLite
5. Test locally, then deploy to Pi #2

**Example Model Export (PyTorch to ONNX)**:
```python
import torch
import torch.onnx

# Assume model is trained
model.eval()

dummy_input = torch.randn(1, num_features)
torch.onnx.export(
    model,
    dummy_input,
    "device_anomaly.onnx",
    input_names=["features"],
    output_names=["anomaly_score"],
    dynamic_axes={"features": {0: "batch_size"}}
)
```

### Model Placement

Place model files in:
```
stacks/ai/models/
├── device_anomaly.onnx      # Device anomaly detection
├── domain_risk.onnx          # Domain risk scoring
└── README.md                 # Model metadata (version, training date, etc.)
```

Models are mounted into the container at `/models/`.

---

## AI Service Configuration

### Environment Variables

Edit `stacks/ai/.env`:

```bash
# Loki connection
LOKI_URL=http://loki:3100

# Pi-hole API (on Pi #1)
PIHOLE_API_URL=http://192.168.1.10/admin/api.php
PIHOLE_API_TOKEN=your-secret-token

# Model paths (inside container)
DEVICE_ANOMALY_MODEL=/models/device_anomaly.onnx
DOMAIN_RISK_MODEL=/models/domain_risk.onnx

# Detection thresholds
DEVICE_ANOMALY_THRESHOLD=0.7
DOMAIN_RISK_THRESHOLD=0.85

# Time windows (minutes)
DEVICE_WINDOW_MINUTES=10
DOMAIN_WINDOW_MINUTES=60

# Batch processing interval (minutes)
BATCH_INTERVAL=10

# Enable enforcement (true/false)
ENABLE_BLOCKING=true

# Logging level
LOG_LEVEL=INFO
```

---

## Python Package Structure

### Module Overview

```
src/orion_ai/
├── __init__.py              # Package init
├── config.py                # Configuration management
├── log_reader.py            # Read logs from Loki
├── feature_extractor.py     # Extract features from logs
├── model_runner.py          # Load and run ML models
├── pipelines.py             # Detection pipeline orchestration
├── output_writer.py         # Write results to Loki
├── http_server.py           # Optional HTTP API
└── pihole_client.py         # Pi-hole API client
```

### config.py

Centralized configuration using environment variables and Pydantic for validation.

**Key Classes**:
- `LokiConfig`: Loki URL, query settings
- `ModelConfig`: Model paths, thresholds
- `PiHoleConfig`: API URL, token
- `DetectionConfig`: Time windows, batch intervals

### log_reader.py

Queries Loki for NSM and DNS logs.

**Key Functions**:
- `get_suricata_flows(start_time, end_time) -> List[Dict]`
- `get_dns_queries(start_time, end_time) -> List[Dict]`
- `get_logs_by_device(device_ip, start_time, end_time) -> Dict`

### feature_extractor.py

Transforms raw log events into numerical feature vectors.

**Key Classes**:
- `DeviceFeatures`: Data class for device-level features
- `DomainFeatures`: Data class for domain-level features

**Key Functions**:
- `extract_device_features(flows, dns_queries) -> DeviceFeatures`
- `extract_domain_features(domain) -> DomainFeatures`

### model_runner.py

Loads ONNX/TFLite models and performs inference.

**Key Class**:
- `ModelRunner`:
  - `load_model(path, format='onnx')`
  - `predict(features) -> np.ndarray`
  - `predict_batch(features_list) -> np.ndarray`

**Performance**:
- Uses AI Hat acceleration via ONNX Runtime
- Batching for efficiency (100+ samples per batch)

### pipelines.py

High-level orchestration for detection pipelines.

**Key Functions**:
- `run_device_anomaly_detection(start_time, end_time) -> List[DeviceAnomalyResult]`
- `run_domain_risk_scoring(start_time, end_time) -> List[DomainRiskResult]`

**Pipeline Logic**:
1. Query logs (log_reader)
2. Extract features (feature_extractor)
3. Run model (model_runner)
4. Apply policy
5. Write results (output_writer)
6. Enforce (pihole_client, if enabled)

### output_writer.py

Writes detection results as structured JSON logs.

**Outputs**:
- JSON logs to file (tailed by Promtail)
- Or direct push to Loki HTTP API

### http_server.py

Optional FastAPI-based HTTP server for:
- `/health`: Health check
- `/metrics`: Prometheus metrics (optional)
- `/api/v1/anomalies`: Get recent device anomalies
- `/api/v1/domains`: Get recent high-risk domains
- `/api/v1/run`: Trigger manual detection run

### pihole_client.py

Client for Pi-hole's HTTP API.

**Key Class**:
- `PiHoleClient`:
  - `add_domain(domain, comment) -> bool`
  - `remove_domain(domain) -> bool`
  - `get_blocklist() -> List[str]`

**Error Handling**:
- Retries with exponential backoff
- Logs all API calls and failures

---

## Execution Modes

### 1. Batch Mode (Default)

Runs detection pipelines on a schedule:

```bash
# In docker-compose.yml
command: python main.py --mode batch --interval 10
```

- Every `BATCH_INTERVAL` minutes:
  - Run device anomaly detection for last window
  - Run domain risk scoring for unique domains in last window
  - Write results to Loki
  - Enforce high-risk domains via Pi-hole

### 2. API Mode

Runs HTTP server for on-demand detection:

```bash
command: python main.py --mode api --port 8080
```

Access API at `http://pi2-ip:8080`

### 3. One-Shot Mode

Run detection once and exit (useful for testing):

```bash
docker compose run orion-ai python main.py --mode oneshot --start "2024-01-15T10:00:00" --end "2024-01-15T11:00:00"
```

---

## Testing and Validation

### 1. Test Feature Extraction

```bash
# Extract features from sample logs
docker compose run orion-ai python -m orion_ai.feature_extractor --test
```

### 2. Test Model Inference

```bash
# Run inference on dummy data
docker compose run orion-ai python -m orion_ai.model_runner --test
```

### 3. Test End-to-End Pipeline

```bash
# Run detection on recent data
docker compose run orion-ai python main.py --mode oneshot --last 1h
```

### 4. Test Pi-hole Integration

```bash
# Test adding/removing a domain
docker compose run orion-ai python -m orion_ai.pihole_client --test-domain test.example.com
```

---

## Performance Tuning

### Resource Limits

In `docker-compose.yml`:

```yaml
services:
  orion-ai:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Batch Size

Larger batches = better throughput, but higher latency:
- Device anomaly: 50-100 devices per batch
- Domain risk: 500-1000 domains per batch

### Time Windows

- Shorter windows (5 min) = faster detection, less data per window
- Longer windows (15 min) = more data, better accuracy

### Model Optimization

- Use ONNX with INT8 quantization for faster inference
- Prune unnecessary model layers
- Use smaller models (fewer parameters)

---

## Troubleshooting

### Models Not Found

**Check**:
```bash
ls -la stacks/ai/models/
```

**Fix**:
Place model files in `models/` directory and update paths in `.env`.

### Inference Errors

**Check logs**:
```bash
docker compose logs orion-ai
```

Common issues:
- Input shape mismatch: Verify feature count matches model input
- Missing dependencies: Install `onnxruntime` or `tflite-runtime`

### No Data from Loki

**Verify Loki has logs**:
```bash
curl "http://localhost:3100/loki/api/v1/query?query={service=\"suricata\"}"
```

**Check AI service Loki URL**:
Ensure `LOKI_URL=http://loki:3100` (internal Docker network).

### Pi-hole API Failures

**Check**:
- Pi-hole is reachable: `curl http://<pi1-ip>/admin/api.php`
- API token is correct
- Network firewall allows connection from Pi #2

**Debug**:
```bash
docker compose run orion-ai python -c "
from orion_ai.pihole_client import PiHoleClient
client = PiHoleClient('http://192.168.1.10/admin/api.php', 'your-token')
print(client.add_domain('test.com', 'test'))
"
```

---

## Future Enhancements

1. **Model Retraining Pipeline**: Automate periodic retraining on new data
2. **Federated Learning**: Share model updates across multiple Orion Sentinel deployments (privacy-preserving)
3. **Explainability**: Add SHAP or LIME for explaining anomaly scores
4. **Multi-Model Ensemble**: Combine multiple models for better accuracy
5. **Active Learning**: Flag uncertain predictions for manual review and retraining
6. **Integration with Threat Intel**: Use external feeds (MISP, AlienVault) as additional features

---

**See Also**:
- [architecture.md](architecture.md) for overall system design
- [pi2-setup.md](pi2-setup.md) for deployment instructions
- [integration-orion-dns-ha.md](integration-orion-dns-ha.md) for Pi-hole API details

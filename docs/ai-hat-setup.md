# AI Hat Setup and Model Training Guide

This guide explains how to set up the Raspberry Pi AI Hat and train models for the Orion Sentinel AI service.

---

## AI Hat Setup

### Hardware Requirements

- **Raspberry Pi 5** (8GB RAM recommended)
- **Raspberry Pi AI HAT+** (Hailo-8L accelerator, ~13 TOPS)
- microSD card (64GB+ recommended)
- Power supply (27W USB-C for Pi 5)

### Installing the AI Hat

1. **Physical Installation**:
   ```bash
   # Power off Pi completely
   sudo shutdown -h now
   
   # Attach AI Hat to GPIO pins (40-pin header)
   # Ensure proper alignment and secure connection
   ```

2. **Enable AI Hat in OS** (Raspberry Pi OS Bookworm):
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Enable HAT overlay
   sudo raspi-config
   # Navigate to: Interfacing Options → I2C → Enable
   # Navigate to: Advanced Options → Expand Filesystem
   
   # Add to /boot/firmware/config.txt
   sudo nano /boot/firmware/config.txt
   ```
   
   Add these lines:
   ```
   # AI Hat configuration
   dtoverlay=hailo-8l
   dtparam=i2c_arm=on
   ```

3. **Install Hailo Runtime**:
   ```bash
   # Install Hailo driver and runtime
   wget https://github.com/hailo-ai/hailort/releases/download/v4.17.0/hailort_4.17.0_arm64.deb
   sudo dpkg -i hailort_4.17.0_arm64.deb
   
   # Install Python bindings
   pip3 install hailort
   
   # Verify installation
   hailortcli fw-control identify
   ```
   
   Expected output:
   ```
   Hailo-8L device found
   Firmware version: 4.17.0
   ```

4. **Test AI Hat**:
   ```bash
   # Run benchmark
   hailortcli benchmark --hef <model.hef>
   
   # Expected performance: ~13 TOPS
   ```

### AI Hat in Docker

The AI service needs access to the Hailo device:

```yaml
# In docker-compose.yml
services:
  orion-ai:
    devices:
      - /dev/hailo0:/dev/hailo0  # AI Hat device
    privileged: false            # Don't need full privileged mode
    cap_add:
      - SYS_RAWIO               # For hardware access
```

**Note**: The current `docker-compose.yml` needs this addition. The AI Hat will be auto-detected by ONNX Runtime when models use Hailo execution provider.

---

## Model Training

The AI service expects **two trained models**:

1. **Device Anomaly Detection Model** (`device_anomaly.onnx`)
2. **Domain Risk Scoring Model** (`domain_risk.onnx`)

### Option 1: Use Pre-trained Models (Recommended for Testing)

**We don't provide pre-trained models** because they must be trained on **your network's baseline**. However, you can:

1. **Use dummy models** for initial testing:
   ```bash
   cd stacks/ai/models/
   
   # The service will create dummy models automatically
   # These return random scores - NOT for production use
   ```

2. **Download community models** (if available):
   - Check Orion Sentinel community forums
   - Models trained on similar home networks
   - **Warning**: May have high false positive rates

### Option 2: Train Your Own Models (Required for Production)

#### Prerequisites

- **Baseline data collection**: 7-30 days of normal network activity
- **Training environment**: Linux machine with Python 3.10+, 16GB+ RAM
- **GPU optional**: For faster training (not required)

#### Step 1: Collect Training Data

Run the NSM stack for at least **7 days** to collect baseline data:

```bash
# On Pi #2, export Suricata and DNS logs
cd /path/to/scripts
./export_training_data.sh --days 7 --output training_data/

# This creates:
# - training_data/flows.jsonl      (Suricata flows)
# - training_data/dns.jsonl        (DNS queries)
# - training_data/alerts.jsonl     (Suricata alerts)
```

#### Step 2: Label Anomalies (Optional but Recommended)

Create a labeled dataset for supervised learning:

```bash
# Review alerts and manually classify
python scripts/label_anomalies.py --input training_data/ --output labeled_data/

# Mark known-good devices/domains as benign
# Mark known-bad activity as malicious
```

If you skip this step, use **unsupervised learning** (anomaly detection only).

#### Step 3: Train Device Anomaly Model

```bash
# Install training dependencies
pip install -r training/requirements.txt

# Train model
python training/train_device_model.py \
  --input labeled_data/ \
  --output models/device_anomaly.onnx \
  --algorithm isolation-forest \
  --features 22 \
  --contamination 0.05

# Algorithm options:
# - isolation-forest: Good for anomaly detection (unsupervised)
# - one-class-svm: Alternative unsupervised method
# - random-forest: Supervised (requires labels)
# - neural-network: Deep learning (requires lots of data)
```

**Training Process**:
1. Load training data (flows, DNS, alerts)
2. Extract features per device per time window
3. Train model on normal behavior
4. Validate on hold-out set
5. Export to ONNX format
6. Quantize for AI Hat (INT8)

**Expected Training Time**:
- Small network (<20 devices): 5-15 minutes
- Medium network (20-100 devices): 30-60 minutes
- Large network (100+ devices): 2-4 hours

#### Step 4: Train Domain Risk Model

```bash
# Train domain risk scoring model
python training/train_domain_model.py \
  --input labeled_data/ \
  --output models/domain_risk.onnx \
  --algorithm gradient-boosting \
  --features 13

# Algorithm options:
# - gradient-boosting: Best for classification (XGBoost)
# - random-forest: Fast, good baseline
# - neural-network: Better accuracy, slower inference
```

**Training Process**:
1. Load DNS queries from baseline period
2. Extract domain features (length, entropy, TLD, etc.)
3. Optionally incorporate threat intel for labeling
4. Train classifier on benign vs malicious
5. Export to ONNX format
6. Quantize for AI Hat

#### Step 5: Optimize for AI Hat

```bash
# Quantize models to INT8 for faster inference
python training/quantize_model.py \
  --input models/device_anomaly.onnx \
  --output models/device_anomaly_int8.onnx \
  --calibration-data training_data/

python training/quantize_model.py \
  --input models/domain_risk.onnx \
  --output models/domain_risk_int8.onnx \
  --calibration-data training_data/
```

**Benefits of Quantization**:
- 3-4x faster inference on AI Hat
- 4x smaller model size
- Minimal accuracy loss (~1-2%)

#### Step 6: Validate Models

```bash
# Test device anomaly model
python training/validate_device_model.py \
  --model models/device_anomaly_int8.onnx \
  --test-data validation_data/ \
  --threshold 0.7

# Expected output:
# - Precision: 80-95% (low false positives)
# - Recall: 70-90% (catches most anomalies)
# - F1 Score: 75-92%

# Test domain risk model  
python training/validate_domain_model.py \
  --model models/domain_risk_int8.onnx \
  --test-data validation_data/ \
  --threshold 0.85

# Expected output:
# - Precision: 85-98% (low false positives for blocking)
# - Recall: 65-85% (catches most bad domains)
# - F1 Score: 75-90%
```

#### Step 7: Deploy Models

```bash
# Copy models to AI service
cd /path/to/orion-sentinel-nsm-ai
cp /path/to/trained/models/*.onnx stacks/ai/models/

# Update .env to use INT8 models
nano stacks/ai/.env
```

Update paths:
```bash
DEVICE_ANOMALY_MODEL=/models/device_anomaly_int8.onnx
DOMAIN_RISK_MODEL=/models/domain_risk_int8.onnx
```

Restart service:
```bash
cd stacks/ai
docker compose down
docker compose up -d
```

---

## Model Retraining

Models should be **retrained periodically** as your network evolves:

### When to Retrain

- **Monthly**: For active/changing networks
- **Quarterly**: For stable networks
- **After major changes**: New devices, network reconfiguration
- **High false positive rate**: Model drift detected

### Automated Retraining

Create a cron job to retrain models:

```bash
# Add to crontab
crontab -e

# Retrain monthly (1st day, 2am)
0 2 1 * * /path/to/scripts/retrain_models.sh
```

`retrain_models.sh`:
```bash
#!/bin/bash
set -e

# Export last 30 days of data
./export_training_data.sh --days 30 --output /tmp/training_data_$(date +%Y%m%d)

# Train models
python training/train_device_model.py --input /tmp/training_data_* --output /tmp/device_model_new.onnx
python training/train_domain_model.py --input /tmp/training_data_* --output /tmp/domain_model_new.onnx

# Validate before deployment
DEVICE_F1=$(python training/validate_device_model.py --model /tmp/device_model_new.onnx | grep F1 | awk '{print $2}')
DOMAIN_F1=$(python training/validate_domain_model.py --model /tmp/domain_model_new.onnx | grep F1 | awk '{print $2}')

# Deploy if validation passes
if (( $(echo "$DEVICE_F1 > 0.70" | bc -l) )) && (( $(echo "$DOMAIN_F1 > 0.70" | bc -l) )); then
    cp /tmp/device_model_new.onnx stacks/ai/models/device_anomaly.onnx
    cp /tmp/domain_model_new.onnx stacks/ai/models/domain_risk.onnx
    docker compose -f stacks/ai/docker-compose.yml restart
    echo "Models updated successfully"
else
    echo "New models failed validation, keeping old models"
fi
```

---

## Training Scripts (To Be Created)

The following scripts need to be created in a `training/` directory:

### Directory Structure

```
training/
├── requirements.txt              # scikit-learn, xgboost, onnx, etc.
├── train_device_model.py         # Train device anomaly model
├── train_domain_model.py         # Train domain risk model
├── validate_device_model.py      # Validate device model
├── validate_domain_model.py      # Validate domain model
├── quantize_model.py             # Quantize to INT8
└── feature_engineering.py        # Feature extraction helpers

scripts/
├── export_training_data.sh       # Export logs from Loki
├── label_anomalies.py            # Interactive labeling tool
└── retrain_models.sh             # Automated retraining
```

### Example: `train_device_model.py`

```python
#!/usr/bin/env python3
"""
Train device anomaly detection model.
"""
import argparse
import json
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import onnxmltools
from skl2onnx import convert_sklearn

# Import feature extraction from AI service
import sys
sys.path.insert(0, '../stacks/ai/src')
from orion_ai.feature_extractor import FeatureExtractor

def load_training_data(input_dir):
    """Load flows, DNS, alerts from training data directory."""
    # Implementation details...
    pass

def extract_features(data):
    """Extract features for all devices."""
    extractor = FeatureExtractor()
    # Implementation details...
    pass

def train_model(X, contamination=0.05):
    """Train Isolation Forest model."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42
    )
    model.fit(X_scaled)
    
    return model, scaler

def export_onnx(model, scaler, output_path):
    """Export to ONNX format."""
    # Convert sklearn model to ONNX
    initial_type = [('float_input', FloatTensorType([None, X.shape[1]]))]
    onnx_model = convert_sklearn(model, initial_types=initial_type)
    
    with open(output_path, 'wb') as f:
        f.write(onnx_model.SerializeToString())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--contamination', type=float, default=0.05)
    args = parser.parse_args()
    
    # Train and export
    data = load_training_data(args.input)
    X = extract_features(data)
    model, scaler = train_model(X, args.contamination)
    export_onnx(model, scaler, args.output)
    print(f"Model saved to {args.output}")
```

---

## Quick Start (Testing Without AI Hat)

For initial testing **without the AI Hat**:

1. **Use CPU inference**:
   ```bash
   # Models will run on CPU via ONNX Runtime
   # Slower but functional for testing
   ```

2. **Use dummy models**:
   ```bash
   # AI service creates dummy models automatically
   # Returns random scores - DO NOT use in production
   ```

3. **Deploy and test**:
   ```bash
   cd stacks/ai
   docker compose up -d
   
   # Check logs
   docker compose logs -f orion-ai
   
   # Should see: "Model loaded: /models/device_anomaly.onnx (CPU execution)"
   ```

---

## Summary

### User Actions Required:

1. **Hardware**:
   - Install AI Hat on Pi 5
   - Enable in OS configuration
   - Install Hailo runtime

2. **Models**:
   - Collect 7-30 days baseline data
   - Train models on your network
   - Validate before deployment
   - Retrain monthly/quarterly

3. **Docker**:
   - Add AI Hat device mapping to docker-compose.yml
   - Deploy trained models to `stacks/ai/models/`

### AI Hat Benefits:

- **13 TOPS inference**: 10-20x faster than CPU
- **Low latency**: Sub-millisecond per domain
- **Efficient**: Low power consumption
- **Scalable**: Can process 1000+ domains/second

### Without AI Hat:

- Models still work on CPU
- Slower inference (10-100ms vs 1ms)
- Higher CPU usage
- Fine for small networks (<50 devices)

# AI Models Directory

This directory should contain the ONNX or TFLite models used by the AI service for threat detection.

## Required Models

### 1. Device Anomaly Detection Model
- **Filename**: `device_anomaly.onnx` (or `.tflite`)
- **Purpose**: Detects unusual network behavior patterns for individual devices
- **Input**: Feature vector (~20-30 numerical features)
- **Output**: Anomaly score (0.0 - 1.0)
- **Model Type**: Autoencoder, Isolation Forest, or One-Class SVM

### 2. Domain Risk Scoring Model
- **Filename**: `domain_risk.onnx` (or `.tflite`)
- **Purpose**: Identifies malicious/suspicious domains (DGA, phishing, C2)
- **Input**: Domain feature vector (~15-20 numerical features)
- **Output**: Risk score (0.0 - 1.0)
- **Model Type**: Binary classifier (Random Forest, XGBoost, Neural Network)

## Model Format

Models should be in **ONNX** format (recommended) or **TFLite** format.

### ONNX (Recommended)
- More flexible, supports most frameworks
- Better tooling and debugging
- Use `onnxruntime` for inference
- **Supports AI Hat acceleration** with Hailo execution provider

### TFLite (Alternative)
- Smaller file size
- Optimized for edge devices
- Requires TensorFlow models

## Obtaining Models

**Note**: This repository does NOT include pre-trained models. You must:

1. **Train your own models** using your network data (recommended for best accuracy)
2. **Use open-source models** from research/community (may require adaptation)
3. **Start with dummy/placeholder models** for testing infrastructure

**IMPORTANT**: Models must be trained on **your network's baseline** behavior. Generic models will have high false positive rates.

## Model Training

**See [docs/ai-hat-setup.md](../../../docs/ai-hat-setup.md) for comprehensive training guide.**

Quick overview:

1. **Collect baseline data** (7-30 days of normal operation)
   - Export Suricata flows and DNS queries from Loki
   - Use scripts in `/scripts/export_training_data.sh`

2. **Train models** on your network baseline
   - Use training scripts in `/training/` directory
   - Train device anomaly model (unsupervised)
   - Train domain risk model (supervised with threat intel)

3. **Optimize for AI Hat** (optional but recommended)
   - Quantize to INT8 for 3-4x speedup
   - Use `/training/quantize_model.py`

4. **Validate performance**
   - Test on validation dataset
   - Aim for F1 score > 0.75

5. **Deploy**
   - Copy `.onnx` files to this directory
   - Update paths in `.env`
   - Restart AI service

### Example Training Commands

```bash
# Train device anomaly model
python training/train_device_model.py \
  --input training_data/ \
  --output models/device_anomaly.onnx \
  --algorithm isolation-forest

# Train domain risk model
python training/train_domain_model.py \
  --input training_data/ \
  --output models/domain_risk.onnx \
  --algorithm gradient-boosting

# Quantize for AI Hat
python training/quantize_model.py \
  --input models/device_anomaly.onnx \
  --output models/device_anomaly_int8.onnx
```

## AI Hat Acceleration

The Raspberry Pi AI Hat (Hailo-8L) provides ~13 TOPS of inference acceleration.

### Benefits:
- **10-20x faster** inference vs CPU
- **Sub-millisecond** latency per domain
- **Low power** consumption
- Can process **1000+ domains/second**

### Requirements:
1. Install AI Hat hardware on Pi 5
2. Install Hailo runtime and drivers
3. Enable device access in docker-compose.yml:
   ```yaml
   devices:
     - /dev/hailo0:/dev/hailo0
   cap_add:
     - SYS_RAWIO
   ```
4. Use quantized models (INT8) for best performance

### Without AI Hat:
- Models run on CPU via ONNX Runtime
- Slower but functional (10-100ms vs 1ms per domain)
- Fine for small networks (<50 devices)

**See [docs/ai-hat-setup.md](../../../docs/ai-hat-setup.md) for AI Hat setup instructions.**

## Model Metadata (Recommended)

For each model, document:
- Training date
- Dataset used
- Feature list and order
- Expected input shape
- Performance metrics (accuracy, precision, recall)
- Version/changelog

Example `device_anomaly_metadata.json`:
```json
{
  "model_name": "device_anomaly.onnx",
  "version": "1.0.0",
  "training_date": "2024-01-15",
  "dataset": "Home network baseline (2024-01-01 to 2024-01-14)",
  "num_features": 25,
  "feature_list": ["connection_count_in", "connection_count_out", ...],
  "input_shape": [1, 25],
  "output_shape": [1, 1],
  "metrics": {
    "precision": 0.85,
    "recall": 0.78,
    "f1": 0.81
  }
}
```

## Placeholder Models (for Testing)

If you don't have models yet, the AI service will:
- Log warnings about missing models
- Continue running without inference
- Allow you to test feature extraction and log reading

To create a minimal dummy ONNX model for testing:

```python
import torch
import torch.nn as nn

class DummyModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.linear = nn.Linear(input_size, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        return self.sigmoid(self.linear(x))

model = DummyModel(25)
dummy_input = torch.randn(1, 25)
torch.onnx.export(model, dummy_input, "device_anomaly.onnx")
```

## Security

- **Do NOT commit large model files** to git (use `.gitignore`)
- Store models securely with version control
- Verify model integrity (checksums) before deployment
- Only use models from trusted sources

## File Size Estimates

- Small model (< 1 MB): Simple linear models
- Medium model (1-50 MB): Random forests, small neural networks
- Large model (50-500 MB): Deep neural networks

Raspberry Pi 5 can handle models up to ~500 MB efficiently with the AI Hat.

---

**See Also**:
- [ai-stack.md](../../../docs/ai-stack.md) for model requirements and specifications
- [feature_extractor.py](../src/orion_ai/feature_extractor.py) for feature definitions

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

### TFLite (Alternative)
- Smaller file size
- Optimized for edge devices
- Requires TensorFlow models

## Obtaining Models

**Note**: This repository does NOT include pre-trained models. You must:

1. **Train your own models** using your network data (recommended for best accuracy)
2. **Use open-source models** from research/community (may require adaptation)
3. **Start with dummy/placeholder models** for testing infrastructure

## Model Training (External)

For best results, train models on data from your own network:

1. **Collect baseline data** (1-2 weeks of normal operation)
   - Export Suricata flows and DNS queries from Loki
   - Label normal behavior vs. anomalies (if available)

2. **Feature engineering**
   - Use `src/orion_ai/feature_extractor.py` as reference
   - Extract same features used in production

3. **Train models** (use Python/Jupyter notebooks separately)
   - Device anomaly: Unsupervised (autoencoder, isolation forest)
   - Domain risk: Supervised (use public DGA/phishing datasets)

4. **Export to ONNX**
   ```python
   # PyTorch example
   import torch
   torch.onnx.export(model, dummy_input, "device_anomaly.onnx")
   
   # TensorFlow example
   import tf2onnx
   tf2onnx.convert.from_keras(model, output_path="domain_risk.onnx")
   ```

5. **Place models here** and update paths in `.env`

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

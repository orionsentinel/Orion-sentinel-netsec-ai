"""
Model runner for ML inference.

Loads and runs ONNX or TFLite models for anomaly detection and risk scoring.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

# Try importing ONNX Runtime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not available. ONNX models cannot be loaded.")

# Try importing TFLite Runtime
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    TFLITE_AVAILABLE = False
    logger.warning("tflite_runtime not available. TFLite models cannot be loaded.")


class ModelRunner:
    """
    ML model runner supporting ONNX and TFLite formats.
    
    Handles model loading, input preprocessing, inference, and output postprocessing.
    """
    
    def __init__(self, model_path: Union[str, Path], model_format: Optional[str] = None):
        """
        Initialize model runner.
        
        Args:
            model_path: Path to model file
            model_format: Model format ('onnx' or 'tflite'). Auto-detected if None.
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If model format is unsupported or runtime unavailable
        """
        self.model_path = Path(model_path)
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Auto-detect format from extension if not provided
        if model_format is None:
            ext = self.model_path.suffix.lower()
            if ext == ".onnx":
                model_format = "onnx"
            elif ext in [".tflite", ".tfl"]:
                model_format = "tflite"
            else:
                raise ValueError(
                    f"Cannot auto-detect model format from extension: {ext}. "
                    "Specify model_format explicitly."
                )
        
        self.model_format = model_format.lower()
        self.model = None
        self.session = None
        self.interpreter = None
        
        logger.info(f"Loading {self.model_format.upper()} model from {model_path}")
        
        if self.model_format == "onnx":
            self._load_onnx()
        elif self.model_format == "tflite":
            self._load_tflite()
        else:
            raise ValueError(f"Unsupported model format: {model_format}")
        
        logger.info(f"Successfully loaded model: {self.model_path.name}")
    
    def _load_onnx(self):
        """Load ONNX model."""
        if not ONNX_AVAILABLE:
            raise ValueError("onnxruntime is not installed. Cannot load ONNX model.")
        
        # Create ONNX Runtime session
        # Use CPUExecutionProvider for compatibility (AI Hat support may require custom provider)
        providers = ["CPUExecutionProvider"]
        
        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=providers
        )
        
        # Get input/output metadata
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
        input_shape = self.session.get_inputs()[0].shape
        output_shape = self.session.get_outputs()[0].shape
        
        logger.info(f"ONNX model input: {self.input_name}, shape: {input_shape}")
        logger.info(f"ONNX model output: {self.output_name}, shape: {output_shape}")
    
    def _load_tflite(self):
        """Load TFLite model."""
        if not TFLITE_AVAILABLE:
            raise ValueError("tflite_runtime is not installed. Cannot load TFLite model.")
        
        # Create TFLite interpreter
        self.interpreter = tflite.Interpreter(model_path=str(self.model_path))
        self.interpreter.allocate_tensors()
        
        # Get input/output details
        input_details = self.interpreter.get_input_details()[0]
        output_details = self.interpreter.get_output_details()[0]
        
        self.input_index = input_details["index"]
        self.output_index = output_details["index"]
        
        logger.info(f"TFLite model input shape: {input_details['shape']}")
        logger.info(f"TFLite model output shape: {output_details['shape']}")
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        Run inference on a single feature vector or batch.
        
        Args:
            features: Input feature array
                - Shape: (num_features,) for single sample
                - Shape: (batch_size, num_features) for batch
                
        Returns:
            Model output (scores/predictions)
                - Shape: (1,) or (batch_size, 1)
        """
        # Ensure 2D shape (batch_size, num_features)
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Ensure float32 dtype
        features = features.astype(np.float32)
        
        if self.model_format == "onnx":
            return self._predict_onnx(features)
        elif self.model_format == "tflite":
            return self._predict_tflite(features)
        else:
            raise ValueError(f"Unknown model format: {self.model_format}")
    
    def _predict_onnx(self, features: np.ndarray) -> np.ndarray:
        """Run ONNX inference."""
        outputs = self.session.run(
            [self.output_name],
            {self.input_name: features}
        )
        return outputs[0]
    
    def _predict_tflite(self, features: np.ndarray) -> np.ndarray:
        """Run TFLite inference."""
        # TFLite typically processes one sample at a time
        # For batch processing, iterate over samples
        results = []
        
        for i in range(features.shape[0]):
            sample = features[i:i+1, :]
            self.interpreter.set_tensor(self.input_index, sample)
            self.interpreter.invoke()
            output = self.interpreter.get_tensor(self.output_index)
            results.append(output[0])
        
        return np.array(results)
    
    def predict_batch(self, features_list: list[np.ndarray]) -> np.ndarray:
        """
        Run inference on a batch of feature vectors.
        
        Args:
            features_list: List of feature arrays
            
        Returns:
            Array of predictions
        """
        # Stack features into batch
        features_batch = np.vstack(features_list)
        return self.predict(features_batch)


class DummyModelRunner:
    """
    Dummy model runner for testing without actual models.
    
    Returns random scores for testing pipeline without ML models.
    """
    
    def __init__(self, model_path: Union[str, Path]):
        """
        Initialize dummy model runner.
        
        Args:
            model_path: Path to (non-existent) model file
        """
        self.model_path = Path(model_path)
        logger.warning(
            f"Using DummyModelRunner for {model_path}. "
            "This is for testing only and returns random scores!"
        )
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        Return random scores.
        
        Args:
            features: Input features (shape: (batch_size, num_features))
            
        Returns:
            Random scores (shape: (batch_size, 1))
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        batch_size = features.shape[0]
        
        # Return random scores between 0 and 1
        scores = np.random.random((batch_size, 1)).astype(np.float32)
        
        logger.debug(f"DummyModelRunner: Generated {batch_size} random scores")
        return scores
    
    def predict_batch(self, features_list: list[np.ndarray]) -> np.ndarray:
        """Return random scores for batch."""
        features_batch = np.vstack(features_list)
        return self.predict(features_batch)


def load_model(model_path: Union[str, Path], use_dummy: bool = False) -> Union[ModelRunner, DummyModelRunner]:
    """
    Load a model with automatic fallback to dummy model.
    
    Args:
        model_path: Path to model file
        use_dummy: Force use of dummy model (for testing)
        
    Returns:
        ModelRunner or DummyModelRunner
    """
    model_path = Path(model_path)
    
    if use_dummy or not model_path.exists():
        if not model_path.exists():
            logger.warning(
                f"Model file not found: {model_path}. "
                "Using dummy model (random scores)."
            )
        return DummyModelRunner(model_path)
    
    try:
        return ModelRunner(model_path)
    except Exception as e:
        logger.error(f"Failed to load model {model_path}: {e}")
        logger.warning("Falling back to dummy model (random scores)")
        return DummyModelRunner(model_path)

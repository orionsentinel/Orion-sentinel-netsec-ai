"""
Automatic Model Trainer

Automatically trains models from collected baseline data.
Handles the full training workflow without user intervention.
"""

import logging
import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Try importing scikit-learn for model training
try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Auto-training disabled.")

# Try importing onnx conversion tools
try:
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    ONNX_CONVERSION_AVAILABLE = True
except ImportError:
    ONNX_CONVERSION_AVAILABLE = False
    logger.warning("skl2onnx not available. ONNX export disabled.")


class AutoTrainer:
    """
    Automatic model trainer that builds models from collected baseline data.
    
    Workflow:
    1. Load collected feature data
    2. Train device anomaly model (unsupervised)
    3. Train domain risk model (supervised with threat intel)
    4. Export to ONNX format
    5. Validate models
    """
    
    def __init__(self, data_dir: Path, model_output_dir: Path):
        """
        Initialize auto trainer.
        
        Args:
            data_dir: Directory containing collected training data
            model_output_dir: Directory to save trained models
        """
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is required for auto-training")
        
        self.data_dir = Path(data_dir)
        self.model_output_dir = Path(model_output_dir)
        self.model_output_dir.mkdir(parents=True, exist_ok=True)
        
        self.device_dir = self.data_dir / "device_features"
        self.domain_dir = self.data_dir / "domain_features"
        
        logger.info(f"Initialized AutoTrainer with data_dir: {data_dir}")
    
    def check_data_readiness(self) -> Tuple[bool, str, Dict]:
        """
        Check if collected data is ready for training.
        
        Returns:
            Tuple of (ready: bool, message: str, stats: dict)
        """
        stats = {
            "device_records": 0,
            "domain_records": 0,
            "collection_days": 0,
            "device_files": 0,
            "domain_files": 0
        }
        
        # Count device records
        device_files = list(self.device_dir.glob("*.jsonl.gz"))
        stats["device_files"] = len(device_files)
        
        for f in device_files:
            try:
                with gzip.open(f, "rt", encoding="utf-8") as file:
                    for line in file:
                        stats["device_records"] += 1
            except Exception as e:
                logger.warning(f"Failed to read {f}: {e}")
        
        # Count domain records
        domain_files = list(self.domain_dir.glob("*.jsonl.gz"))
        stats["domain_files"] = len(domain_files)
        
        for f in domain_files:
            try:
                with gzip.open(f, "rt", encoding="utf-8") as file:
                    for line in file:
                        stats["domain_records"] += 1
            except Exception as e:
                logger.warning(f"Failed to read {f}: {e}")
        
        # Estimate collection days from file names
        dates = []
        for f in list(device_files) + list(domain_files):
            try:
                date_str = f.stem.split("_")[-1]
                dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            except (ValueError, IndexError):
                continue
        
        if dates:
            stats["collection_days"] = (max(dates) - min(dates)).days + 1
        
        # Check readiness criteria
        min_device_records = 1000  # At least 1000 device observations
        min_domain_records = 5000  # At least 5000 domain observations
        min_days = 7  # At least 7 days of data
        
        if stats["device_records"] < min_device_records:
            return False, f"Not enough device data ({stats['device_records']}/{min_device_records})", stats
        
        if stats["domain_records"] < min_domain_records:
            return False, f"Not enough domain data ({stats['domain_records']}/{min_domain_records})", stats
        
        if stats["collection_days"] < min_days:
            return False, f"Not enough collection days ({stats['collection_days']}/{min_days})", stats
        
        return True, "Data ready for training", stats
    
    def load_device_features(self) -> Tuple[np.ndarray, List[str]]:
        """
        Load all collected device features.
        
        Returns:
            Tuple of (features array, device IPs list)
        """
        logger.info("Loading device features...")
        
        features_list = []
        device_ips = []
        
        for f in sorted(self.device_dir.glob("*.jsonl.gz")):
            try:
                with gzip.open(f, "rt", encoding="utf-8") as file:
                    for line in file:
                        record = json.loads(line)
                        features_list.append(record["feature_vector"])
                        device_ips.append(record["device_ip"])
            except Exception as e:
                logger.warning(f"Failed to load {f}: {e}")
        
        features = np.array(features_list, dtype=np.float32)
        logger.info(f"Loaded {len(features)} device feature vectors (shape: {features.shape})")
        
        return features, device_ips
    
    def load_domain_features(self) -> Tuple[np.ndarray, List[str], np.ndarray]:
        """
        Load all collected domain features.
        
        Returns:
            Tuple of (features array, domains list, labels array)
        """
        logger.info("Loading domain features...")
        
        features_list = []
        domains = []
        labels = []  # Will be populated from threat intel if available
        
        for f in sorted(self.domain_dir.glob("*.jsonl.gz")):
            try:
                with gzip.open(f, "rt", encoding="utf-8") as file:
                    for line in file:
                        record = json.loads(line)
                        features_list.append(record["feature_vector"])
                        domains.append(record["domain"])
                        # Default label: 0 (benign)
                        # Could enhance with threat intel matching
                        labels.append(0)
            except Exception as e:
                logger.warning(f"Failed to load {f}: {e}")
        
        features = np.array(features_list, dtype=np.float32)
        labels = np.array(labels, dtype=np.int32)
        
        logger.info(f"Loaded {len(features)} domain feature vectors (shape: {features.shape})")
        
        return features, domains, labels
    
    def train_device_anomaly_model(self) -> bool:
        """
        Train device anomaly detection model using Isolation Forest.
        
        Returns:
            True if successful
        """
        logger.info("="*80)
        logger.info("Training Device Anomaly Detection Model")
        logger.info("="*80)
        
        try:
            # Load features
            features, device_ips = self.load_device_features()
            
            if len(features) < 100:
                logger.error(f"Not enough data to train ({len(features)} samples)")
                return False
            
            # Normalize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Train Isolation Forest
            logger.info("Training Isolation Forest model...")
            model = IsolationForest(
                n_estimators=100,
                max_samples='auto',
                contamination=0.1,  # Assume 10% anomalies
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(features_scaled)
            
            # Test predictions
            predictions = model.predict(features_scaled)
            anomaly_count = np.sum(predictions == -1)
            logger.info(f"Model detected {anomaly_count}/{len(predictions)} anomalies in training data")
            
            # Save model
            model_path = self.model_output_dir / "device_anomaly_model.pkl"
            scaler_path = self.model_output_dir / "device_anomaly_scaler.pkl"
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            logger.info(f"✓ Saved model to {model_path}")
            
            # Export to ONNX if available
            if ONNX_CONVERSION_AVAILABLE:
                try:
                    self._export_to_onnx(
                        model, scaler, features_scaled[0:1],
                        "device_anomaly.onnx"
                    )
                except Exception as e:
                    logger.warning(f"ONNX export failed: {e}")
            
            logger.info("✓ Device anomaly model training complete")
            return True
            
        except Exception as e:
            logger.error(f"Device model training failed: {e}", exc_info=True)
            return False
    
    def train_domain_risk_model(self) -> bool:
        """
        Train domain risk scoring model.
        
        Since we don't have labeled malicious domains in baseline,
        we use a simple heuristic model initially.
        
        Returns:
            True if successful
        """
        logger.info("="*80)
        logger.info("Training Domain Risk Scoring Model")
        logger.info("="*80)
        
        try:
            # Load features
            features, domains, labels = self.load_domain_features()
            
            if len(features) < 100:
                logger.error(f"Not enough data to train ({len(features)} samples)")
                return False
            
            # For baseline training without labeled data, we'll create a simple
            # Random Forest that learns normal patterns
            logger.info("Training Random Forest classifier...")
            
            # Normalize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Since we don't have true malicious labels, we'll train on
            # features that predict "normal" vs statistical outliers
            # This is a semi-supervised approach
            
            # Use Isolation Forest to generate pseudo-labels
            iso_forest = IsolationForest(contamination=0.05, random_state=42)
            pseudo_labels = iso_forest.fit_predict(features_scaled)
            # Convert: -1 (anomaly) -> 1 (risky), 1 (normal) -> 0 (safe)
            pseudo_labels = np.where(pseudo_labels == -1, 1, 0)
            
            logger.info(f"Generated pseudo-labels: {np.sum(pseudo_labels)} risky domains")
            
            # Train Random Forest on pseudo-labels
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(features_scaled, pseudo_labels)
            
            # Save model
            model_path = self.model_output_dir / "domain_risk_model.pkl"
            scaler_path = self.model_output_dir / "domain_risk_scaler.pkl"
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            logger.info(f"✓ Saved model to {model_path}")
            
            # Export to ONNX if available
            if ONNX_CONVERSION_AVAILABLE:
                try:
                    self._export_to_onnx(
                        model, scaler, features_scaled[0:1],
                        "domain_risk.onnx"
                    )
                except Exception as e:
                    logger.warning(f"ONNX export failed: {e}")
            
            logger.info("✓ Domain risk model training complete")
            logger.info("  Note: Model trained on baseline patterns. Update with labeled")
            logger.info("        malicious samples for better accuracy.")
            
            return True
            
        except Exception as e:
            logger.error(f"Domain model training failed: {e}", exc_info=True)
            return False
    
    def _export_to_onnx(self, model, scaler, sample_input, output_name):
        """
        Export sklearn model to ONNX format.
        
        Args:
            model: Trained sklearn model
            scaler: Feature scaler
            sample_input: Sample input for shape inference
            output_name: Output ONNX filename
        """
        logger.info(f"Exporting to ONNX: {output_name}")
        
        # Create pipeline with scaler and model
        from sklearn.pipeline import Pipeline
        pipeline = Pipeline([
            ('scaler', scaler),
            ('model', model)
        ])
        
        # Define input type
        n_features = sample_input.shape[1]
        initial_type = [('float_input', FloatTensorType([None, n_features]))]
        
        # Convert to ONNX
        onnx_model = convert_sklearn(pipeline, initial_types=initial_type)
        
        # Save
        output_path = self.model_output_dir / output_name
        with open(output_path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        
        logger.info(f"✓ Exported to {output_path}")
    
    def train_all(self) -> bool:
        """
        Train all models automatically.
        
        Returns:
            True if all models trained successfully
        """
        logger.info("="*80)
        logger.info("AUTOMATIC MODEL TRAINING")
        logger.info("="*80)
        
        # Check data readiness
        ready, message, stats = self.check_data_readiness()
        
        logger.info(f"Data readiness check: {message}")
        logger.info(f"  Device records: {stats['device_records']}")
        logger.info(f"  Domain records: {stats['domain_records']}")
        logger.info(f"  Collection days: {stats['collection_days']}")
        
        if not ready:
            logger.warning("Data not ready for training yet")
            return False
        
        logger.info("✓ Data ready for training!")
        logger.info("")
        
        # Train models
        device_success = self.train_device_anomaly_model()
        domain_success = self.train_domain_risk_model()
        
        if device_success and domain_success:
            logger.info("="*80)
            logger.info("✓ ALL MODELS TRAINED SUCCESSFULLY!")
            logger.info("="*80)
            logger.info(f"Models saved to: {self.model_output_dir}")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. System will automatically switch to detection mode")
            logger.info("2. Monitor detection results in Grafana")
            logger.info("3. Retrain models monthly with updated baseline")
            logger.info("="*80)
            return True
        else:
            logger.error("Model training failed")
            return False

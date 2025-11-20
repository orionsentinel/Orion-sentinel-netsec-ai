"""
Output writer for AI detection results.

Writes detection results as structured JSON logs for Promtail/Loki ingestion.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from orion_ai.config import get_config

logger = logging.getLogger(__name__)


class OutputWriter:
    """
    Writes AI detection results as JSON logs.
    
    Results are written to files that Promtail can tail and ship to Loki.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize output writer.
        
        Args:
            output_dir: Directory for output files (default from config)
        """
        config = get_config()
        self.output_dir = Path(output_dir or config.log_output_dir)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate files for different log types
        self.device_anomaly_file = self.output_dir / "device_anomaly.json"
        self.domain_risk_file = self.output_dir / "domain_risk.json"
        
        logger.info(f"Initialized OutputWriter with output_dir={self.output_dir}")
    
    def write_device_anomaly(
        self,
        device_ip: str,
        window_start: datetime,
        window_end: datetime,
        anomaly_score: float,
        features: Dict[str, Any],
        threshold: float
    ) -> None:
        """
        Write device anomaly detection result.
        
        Args:
            device_ip: Device IP address
            window_start: Time window start
            window_end: Time window end
            anomaly_score: Computed anomaly score (0.0 - 1.0)
            features: Dictionary of extracted features
            threshold: Threshold used for alerting
        """
        # Determine severity based on score
        if anomaly_score >= 0.9:
            severity = "critical"
        elif anomaly_score >= threshold:
            severity = "warning"
        else:
            severity = "info"
        
        # Identify top anomalies (features that are unusual)
        # This is a simplified heuristic - real implementation would compare to baseline
        top_anomalies = []
        if features.get("unique_dest_ips", 0) > 50:
            top_anomalies.append(
                f"high unique_dest_ips ({features['unique_dest_ips']})"
            )
        if features.get("nxdomain_ratio", 0) > 0.2:
            top_anomalies.append(
                f"high nxdomain_ratio ({features['nxdomain_ratio']:.2f})"
            )
        if features.get("rare_port_count", 0) > 20:
            top_anomalies.append(
                f"high rare_port_count ({features['rare_port_count']})"
            )
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "service": "ai-device-anomaly",
            "severity": severity,
            "device_ip": device_ip,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "anomaly_score": round(anomaly_score, 4),
            "threshold": threshold,
            "features": features,
            "top_anomalies": top_anomalies
        }
        
        self._write_json_line(self.device_anomaly_file, result)
        
        if severity in ["warning", "critical"]:
            logger.info(
                f"Device anomaly detected: {device_ip} "
                f"(score={anomaly_score:.3f}, severity={severity})"
            )
    
    def write_domain_risk(
        self,
        domain: str,
        risk_score: float,
        features: Dict[str, Any],
        action: str,
        threshold: float,
        reason: Optional[str] = None,
        pihole_response: Optional[str] = None
    ) -> None:
        """
        Write domain risk scoring result.
        
        Args:
            domain: Domain name
            risk_score: Computed risk score (0.0 - 1.0)
            features: Dictionary of extracted features
            action: Action taken (ALLOW, BLOCK, NO_CHANGE)
            threshold: Threshold used for blocking
            reason: Human-readable reason for score (optional)
            pihole_response: Response from Pi-hole API (optional)
        """
        # Determine severity
        if risk_score >= threshold:
            severity = "critical"
        elif risk_score >= 0.7:
            severity = "warning"
        else:
            severity = "info"
        
        # Generate reason if not provided
        if reason is None:
            reasons = []
            if features.get("char_entropy", 0) > 3.5:
                reasons.append("high entropy")
            if features.get("tld_category") == "suspicious":
                reasons.append("suspicious TLD")
            if features.get("max_consonant_streak", 0) > 7:
                reasons.append("DGA-like pattern")
            if features.get("digit_ratio", 0) > 0.3:
                reasons.append("high digit ratio")
            
            reason = ", ".join(reasons) if reasons else "ML model score"
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "service": "ai-domain-risk",
            "severity": severity,
            "domain": domain,
            "risk_score": round(risk_score, 4),
            "threshold": threshold,
            "action": action,
            "features": features,
            "reason": reason
        }
        
        if pihole_response:
            result["pihole_response"] = pihole_response
        
        self._write_json_line(self.domain_risk_file, result)
        
        if action == "BLOCK":
            logger.warning(
                f"High-risk domain blocked: {domain} "
                f"(score={risk_score:.3f}, reason={reason})"
            )
        elif severity == "warning":
            logger.info(
                f"Potentially risky domain: {domain} "
                f"(score={risk_score:.3f}, action={action})"
            )
    
    def _write_json_line(self, filepath: Path, data: Dict[str, Any]) -> None:
        """
        Write a single JSON line to file.
        
        Args:
            filepath: Path to output file
            data: Data to write as JSON
        """
        try:
            with filepath.open("a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to {filepath}: {e}")


class ConsoleOutputWriter:
    """
    Console-only output writer for testing.
    
    Prints results to console instead of writing to files.
    """
    
    def __init__(self):
        """Initialize console output writer."""
        logger.info("Initialized ConsoleOutputWriter (console output only)")
    
    def write_device_anomaly(
        self,
        device_ip: str,
        window_start: datetime,
        window_end: datetime,
        anomaly_score: float,
        features: Dict[str, Any],
        threshold: float
    ) -> None:
        """Print device anomaly result to console."""
        severity = "critical" if anomaly_score >= 0.9 else "warning" if anomaly_score >= threshold else "info"
        
        print(f"\n{'='*80}")
        print(f"DEVICE ANOMALY DETECTION")
        print(f"{'='*80}")
        print(f"Device IP:      {device_ip}")
        print(f"Time Window:    {window_start} to {window_end}")
        print(f"Anomaly Score:  {anomaly_score:.4f} (threshold: {threshold})")
        print(f"Severity:       {severity}")
        print(f"\nFeatures:")
        for key, value in features.items():
            print(f"  {key:30s}: {value}")
        print(f"{'='*80}\n")
    
    def write_domain_risk(
        self,
        domain: str,
        risk_score: float,
        features: Dict[str, Any],
        action: str,
        threshold: float,
        reason: Optional[str] = None,
        pihole_response: Optional[str] = None
    ) -> None:
        """Print domain risk result to console."""
        severity = "critical" if risk_score >= threshold else "warning" if risk_score >= 0.7 else "info"
        
        print(f"\n{'='*80}")
        print(f"DOMAIN RISK SCORING")
        print(f"{'='*80}")
        print(f"Domain:         {domain}")
        print(f"Risk Score:     {risk_score:.4f} (threshold: {threshold})")
        print(f"Severity:       {severity}")
        print(f"Action:         {action}")
        if reason:
            print(f"Reason:         {reason}")
        if pihole_response:
            print(f"Pi-hole:        {pihole_response}")
        print(f"\nFeatures:")
        for key, value in features.items():
            print(f"  {key:30s}: {value}")
        print(f"{'='*80}\n")

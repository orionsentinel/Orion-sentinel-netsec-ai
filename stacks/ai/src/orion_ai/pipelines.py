"""
Detection pipelines for device anomaly detection and domain risk scoring.

Orchestrates the full workflow from log reading to model inference to enforcement.
Includes threat intelligence integration for enhanced detection.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from orion_ai.config import get_config
from orion_ai.log_reader import LokiLogReader
from orion_ai.feature_extractor import FeatureExtractor
from orion_ai.model_runner import load_model
from orion_ai.output_writer import OutputWriter
from orion_ai.pihole_client import PiHoleClient, DummyPiHoleClient
from orion_ai.threat_intel import ThreatIntelligenceService

logger = logging.getLogger(__name__)


@dataclass
class DeviceAnomalyResult:
    """Result from device anomaly detection."""
    device_ip: str
    window_start: datetime
    window_end: datetime
    anomaly_score: float
    features: Dict
    threshold: float
    is_anomalous: bool


@dataclass
class DomainRiskResult:
    """Result from domain risk scoring."""
    domain: str
    risk_score: float
    features: Dict
    threshold: float
    action: str  # ALLOW, BLOCK
    reason: str


class DeviceAnomalyPipeline:
    """
    Pipeline for device anomaly detection.
    
    Workflow:
    1. Read Suricata flows, DNS queries, and alerts from Loki
    2. Group by source IP (device)
    3. Extract features per device
    4. Run anomaly detection model
    5. Write results to logs
    """
    
    def __init__(self):
        """Initialize device anomaly pipeline."""
        self.config = get_config()
        self.log_reader = LokiLogReader()
        self.feature_extractor = FeatureExtractor()
        self.output_writer = OutputWriter()
        
        # Load model (with auto-fallback to dummy if not found)
        model_path = self.config.model.device_anomaly_model
        self.model = load_model(model_path, use_dummy=False)
        
        logger.info("Initialized DeviceAnomalyPipeline")
    
    def run(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[DeviceAnomalyResult]:
        """
        Run device anomaly detection for a time window.
        
        Args:
            start_time: Start of time window (default: now - window_minutes)
            end_time: End of time window (default: now)
            
        Returns:
            List of DeviceAnomalyResult objects
        """
        # Default time window
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            window_minutes = self.config.detection.device_window_minutes
            start_time = end_time - timedelta(minutes=window_minutes)
        
        logger.info(
            f"Running device anomaly detection for window: "
            f"{start_time} to {end_time}"
        )
        
        # Read logs from Loki
        try:
            flows = self.log_reader.get_suricata_flows(start_time, end_time)
            dns_queries = self.log_reader.get_dns_queries(start_time, end_time)
            alerts = self.log_reader.get_suricata_alerts(start_time, end_time)
            
            logger.info(
                f"Retrieved {len(flows)} flows, "
                f"{len(dns_queries)} DNS queries, "
                f"{len(alerts)} alerts"
            )
        except Exception as e:
            logger.error(f"Failed to read logs from Loki: {e}")
            return []
        
        # Group logs by device IP
        device_logs = self._group_by_device(flows, dns_queries, alerts)
        
        logger.info(f"Processing {len(device_logs)} unique devices")
        
        # Process each device
        results = []
        for device_ip, logs in device_logs.items():
            try:
                result = self._process_device(
                    device_ip,
                    logs["flows"],
                    logs["dns_queries"],
                    logs["alerts"],
                    start_time,
                    end_time
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to process device {device_ip}: {e}")
        
        logger.info(
            f"Device anomaly detection complete: "
            f"{len(results)} devices processed, "
            f"{sum(1 for r in results if r.is_anomalous)} anomalies detected"
        )
        
        return results
    
    def _group_by_device(
        self,
        flows: List[Dict],
        dns_queries: List[Dict],
        alerts: List[Dict]
    ) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Group logs by device IP (source IP).
        
        Returns:
            Dictionary: {device_ip: {flows: [...], dns_queries: [...], alerts: [...]}}
        """
        device_logs = {}
        
        # Helper to extract IP from log entry
        def get_src_ip(entry: Dict) -> Optional[str]:
            try:
                import json
                log = json.loads(entry.get("log", "{}"))
                return log.get("src_ip")
            except:
                return None
        
        # Group flows
        for flow in flows:
            src_ip = get_src_ip(flow)
            if src_ip:
                if src_ip not in device_logs:
                    device_logs[src_ip] = {"flows": [], "dns_queries": [], "alerts": []}
                device_logs[src_ip]["flows"].append(flow)
        
        # Group DNS queries
        for dns in dns_queries:
            src_ip = get_src_ip(dns)
            if src_ip:
                if src_ip not in device_logs:
                    device_logs[src_ip] = {"flows": [], "dns_queries": [], "alerts": []}
                device_logs[src_ip]["dns_queries"].append(dns)
        
        # Group alerts
        for alert in alerts:
            src_ip = get_src_ip(alert)
            if src_ip:
                if src_ip not in device_logs:
                    device_logs[src_ip] = {"flows": [], "dns_queries": [], "alerts": []}
                device_logs[src_ip]["alerts"].append(alert)
        
        return device_logs
    
    def _process_device(
        self,
        device_ip: str,
        flows: List[Dict],
        dns_queries: List[Dict],
        alerts: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> Optional[DeviceAnomalyResult]:
        """
        Process a single device: extract features, run model, write results.
        
        Returns:
            DeviceAnomalyResult or None if processing failed
        """
        # Extract features
        features = self.feature_extractor.extract_device_features(
            device_ip=device_ip,
            flows=flows,
            dns_queries=dns_queries,
            alerts=alerts,
            window_start=start_time,
            window_end=end_time
        )
        
        # Convert to feature vector
        feature_vector = features.to_vector()
        
        # Run model
        try:
            prediction = self.model.predict(feature_vector)
            anomaly_score = float(prediction[0][0])  # Extract scalar score
        except Exception as e:
            logger.error(f"Model inference failed for device {device_ip}: {e}")
            return None
        
        # Determine if anomalous
        threshold = self.config.model.device_anomaly_threshold
        is_anomalous = anomaly_score >= threshold
        
        # Create result
        result = DeviceAnomalyResult(
            device_ip=device_ip,
            window_start=start_time,
            window_end=end_time,
            anomaly_score=anomaly_score,
            features=features.to_dict(),
            threshold=threshold,
            is_anomalous=is_anomalous
        )
        
        # Write result to logs
        self.output_writer.write_device_anomaly(
            device_ip=device_ip,
            window_start=start_time,
            window_end=end_time,
            anomaly_score=anomaly_score,
            features=features.to_dict(),
            threshold=threshold
        )
        
        return result


class DomainRiskPipeline:
    """
    Pipeline for domain risk scoring.
    
    Workflow:
    1. Read DNS queries from Loki
    2. Extract unique domains
    3. Extract features per domain
    4. Run risk scoring model
    5. Apply policy (block if score >= threshold)
    6. Call Pi-hole API if blocking
    7. Write results to logs
    """
    
    def __init__(self):
        """Initialize domain risk pipeline."""
        self.config = get_config()
        self.log_reader = LokiLogReader()
        self.feature_extractor = FeatureExtractor()
        self.output_writer = OutputWriter()
        
        # Load model
        model_path = self.config.model.domain_risk_model
        self.model = load_model(model_path, use_dummy=False)
        
        # Pi-hole client (use dummy if blocking disabled)
        if self.config.detection.enable_blocking:
            self.pihole_client = PiHoleClient()
        else:
            logger.info("Blocking disabled - using dummy Pi-hole client")
            self.pihole_client = DummyPiHoleClient()
        
        # Threat intelligence service (if enabled)
        if self.config.threat_intel.enable_threat_intel:
            self.threat_intel = ThreatIntelligenceService(
                cache_path=self.config.threat_intel.cache_path,
                otx_api_key=self.config.threat_intel.otx_api_key,
                refresh_interval_hours=self.config.threat_intel.refresh_interval_hours
            )
            logger.info("Threat intelligence integration enabled")
        else:
            self.threat_intel = None
            logger.info("Threat intelligence integration disabled")
        
        logger.info("Initialized DomainRiskPipeline")
    
    def run(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[DomainRiskResult]:
        """
        Run domain risk scoring for a time window.
        
        Args:
            start_time: Start of time window (default: now - window_minutes)
            end_time: End of time window (default: now)
            
        Returns:
            List of DomainRiskResult objects
        """
        # Default time window
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            window_minutes = self.config.detection.domain_window_minutes
            start_time = end_time - timedelta(minutes=window_minutes)
        
        logger.info(
            f"Running domain risk scoring for window: "
            f"{start_time} to {end_time}"
        )
        
        # Read DNS queries
        try:
            dns_queries = self.log_reader.get_dns_queries(start_time, end_time)
            logger.info(f"Retrieved {len(dns_queries)} DNS queries")
        except Exception as e:
            logger.error(f"Failed to read DNS queries from Loki: {e}")
            return []
        
        # Extract unique domains
        domain_counts = self._extract_unique_domains(dns_queries)
        
        logger.info(f"Processing {len(domain_counts)} unique domains")
        
        # Process each domain
        results = []
        for domain, query_count in domain_counts.items():
            try:
                result = self._process_domain(domain, query_count)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to process domain {domain}: {e}")
        
        blocked_count = sum(1 for r in results if r.action == "BLOCK")
        logger.info(
            f"Domain risk scoring complete: "
            f"{len(results)} domains processed, "
            f"{blocked_count} domains blocked"
        )
        
        return results
    
    def _extract_unique_domains(self, dns_queries: List[Dict]) -> Dict[str, int]:
        """
        Extract unique domains from DNS queries with query counts.
        
        Returns:
            Dictionary: {domain: query_count}
        """
        import json
        from collections import Counter
        
        domains = []
        
        for entry in dns_queries:
            try:
                log = json.loads(entry.get("log", "{}"))
                dns_data = log.get("dns", {})
                
                if dns_data.get("type") == "query":
                    domain = dns_data.get("rrname", "").lower().strip(".")
                    if domain:
                        domains.append(domain)
            except:
                continue
        
        return dict(Counter(domains))
    
    def _process_domain(
        self,
        domain: str,
        query_count: int
    ) -> Optional[DomainRiskResult]:
        """
        Process a single domain: extract features, run model, apply policy.
        
        Returns:
            DomainRiskResult or None if processing failed
        """
        # Check threat intelligence first (if enabled)
        threat_indicator = None
        if self.threat_intel:
            threat_indicator = self.threat_intel.check_domain(domain)
        
        # Extract features
        features = self.feature_extractor.extract_domain_features(
            domain=domain,
            query_count=query_count
        )
        
        # Convert to feature vector
        feature_vector = features.to_vector()
        
        # Run model
        try:
            prediction = self.model.predict(feature_vector)
            risk_score = float(prediction[0][0])  # Extract scalar score
        except Exception as e:
            logger.error(f"Model inference failed for domain {domain}: {e}")
            return None
        
        # Boost risk score if threat intelligence match found
        original_score = risk_score
        if threat_indicator:
            ioc_boost = self.config.threat_intel.ioc_score_boost
            risk_score = min(1.0, risk_score + ioc_boost)
            logger.warning(
                f"Threat intel match for {domain}: {threat_indicator.threat_type.value} "
                f"from {threat_indicator.source} (confidence={threat_indicator.confidence:.2f}). "
                f"Score boosted from {original_score:.3f} to {risk_score:.3f}"
            )
        
        # Apply policy
        threshold = self.config.model.domain_risk_threshold
        action, reason = self._apply_policy(
            domain, risk_score, threshold, features.to_dict(), threat_indicator
        )
        
        # Enforce if action is BLOCK
        pihole_response = None
        if action == "BLOCK":
            pihole_response = self._enforce_block(domain, risk_score)
        
        # Add threat intel info to features if present
        features_dict = features.to_dict()
        if threat_indicator:
            features_dict["threat_intel_match"] = {
                "source": threat_indicator.source,
                "threat_type": threat_indicator.threat_type.value,
                "confidence": threat_indicator.confidence,
                "description": threat_indicator.description
            }
        
        # Create result
        result = DomainRiskResult(
            domain=domain,
            risk_score=risk_score,
            features=features_dict,
            threshold=threshold,
            action=action,
            reason=reason
        )
        
        # Write result to logs
        self.output_writer.write_domain_risk(
            domain=domain,
            risk_score=risk_score,
            features=features_dict,
            action=action,
            threshold=threshold,
            reason=reason,
            pihole_response=pihole_response
        )
        
        return result
    
    def _apply_policy(
        self,
        domain: str,
        risk_score: float,
        threshold: float,
        features: Dict,
        threat_indicator=None
    ) -> Tuple[str, str]:
        """
        Apply blocking policy.
        
        Returns:
            Tuple of (action, reason)
        """
        if threat_indicator:
            # If threat intel match, include in reason
            if risk_score >= threshold:
                return "BLOCK", (
                    f"Risk score {risk_score:.3f} >= threshold {threshold} "
                    f"+ Threat intel match ({threat_indicator.source})"
                )
            else:
                # Even below threshold, mention threat intel match
                return "ALLOW", (
                    f"Risk score {risk_score:.3f} < threshold {threshold} "
                    f"but flagged by {threat_indicator.source}"
                )
        else:
            if risk_score >= threshold:
                return "BLOCK", f"Risk score {risk_score:.3f} >= threshold {threshold}"
            else:
                return "ALLOW", f"Risk score {risk_score:.3f} < threshold {threshold}"
    
    def _enforce_block(self, domain: str, risk_score: float) -> Optional[str]:
        """
        Enforce blocking via Pi-hole API.
        
        Returns:
            Response string or None
        """
        comment = f"AI-detected risk: score={risk_score:.3f}"
        
        try:
            success = self.pihole_client.add_domain(domain, comment=comment)
            if success:
                return "success"
            else:
                return "failed"
        except Exception as e:
            logger.error(f"Failed to block domain {domain} via Pi-hole: {e}")
            return f"error: {str(e)}"

"""
Feature extraction for AI models.

Transforms raw log events into numerical feature vectors for ML inference.
"""

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Set
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DeviceFeatures:
    """
    Feature vector for device anomaly detection.
    
    Represents aggregated network behavior for a single device
    over a time window.
    """
    
    # Device identification
    device_ip: str
    window_start: datetime
    window_end: datetime
    
    # Connection features
    connection_count_in: int = 0
    connection_count_out: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    unique_dest_ips: int = 0
    unique_dest_ports: int = 0
    
    # Protocol distribution
    protocol_tcp_ratio: float = 0.0
    protocol_udp_ratio: float = 0.0
    protocol_icmp_ratio: float = 0.0
    
    # DNS features
    dns_query_count: int = 0
    unique_domains: int = 0
    avg_domain_length: float = 0.0
    avg_domain_entropy: float = 0.0
    nxdomain_ratio: float = 0.0
    
    # Timing features
    avg_connection_duration: float = 0.0
    connection_rate_per_minute: float = 0.0
    
    # Port patterns
    common_port_ratio: float = 0.0  # % connections to ports 80/443
    rare_port_count: int = 0        # Connections to unusual ports (>1024)
    
    # Data transfer patterns
    avg_bytes_per_connection: float = 0.0
    upload_download_ratio: float = 0.0
    
    # Alert features
    alert_count: int = 0
    unique_alert_signatures: int = 0
    
    def to_vector(self) -> np.ndarray:
        """
        Convert features to numpy array for model input.
        
        Returns:
            1D numpy array of numerical features
        """
        features = [
            self.connection_count_in,
            self.connection_count_out,
            self.bytes_sent,
            self.bytes_received,
            self.unique_dest_ips,
            self.unique_dest_ports,
            self.protocol_tcp_ratio,
            self.protocol_udp_ratio,
            self.protocol_icmp_ratio,
            self.dns_query_count,
            self.unique_domains,
            self.avg_domain_length,
            self.avg_domain_entropy,
            self.nxdomain_ratio,
            self.avg_connection_duration,
            self.connection_rate_per_minute,
            self.common_port_ratio,
            self.rare_port_count,
            self.avg_bytes_per_connection,
            self.upload_download_ratio,
            self.alert_count,
            self.unique_alert_signatures
        ]
        return np.array(features, dtype=np.float32)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return asdict(self)


@dataclass
class DomainFeatures:
    """
    Feature vector for domain risk scoring.
    
    Represents characteristics of a single domain name.
    """
    
    # Domain identification
    domain: str
    
    # Length features
    domain_length: int = 0
    subdomain_count: int = 0
    tld_length: int = 0
    
    # Character features
    char_entropy: float = 0.0
    vowel_ratio: float = 0.0
    consonant_ratio: float = 0.0
    digit_ratio: float = 0.0
    special_char_count: int = 0
    
    # Pattern features
    has_ip_pattern: bool = False
    max_consonant_streak: int = 0
    hex_ratio: float = 0.0
    
    # TLD features
    tld: str = ""
    tld_category: str = "unknown"  # common, rare, suspicious
    
    # Query frequency (if available)
    query_count: int = 0
    
    def to_vector(self) -> np.ndarray:
        """
        Convert features to numpy array for model input.
        
        Returns:
            1D numpy array of numerical features
        """
        # Convert boolean to int
        has_ip_int = 1 if self.has_ip_pattern else 0
        
        # Convert TLD category to numeric
        tld_category_map = {"common": 0, "rare": 1, "suspicious": 2, "unknown": 1}
        tld_category_int = tld_category_map.get(self.tld_category, 1)
        
        features = [
            self.domain_length,
            self.subdomain_count,
            self.tld_length,
            self.char_entropy,
            self.vowel_ratio,
            self.consonant_ratio,
            self.digit_ratio,
            self.special_char_count,
            has_ip_int,
            self.max_consonant_streak,
            self.hex_ratio,
            tld_category_int,
            self.query_count
        ]
        return np.array(features, dtype=np.float32)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return asdict(self)


class FeatureExtractor:
    """
    Feature extractor for NSM and DNS logs.
    
    Processes raw Suricata and DNS events to create feature vectors
    for device anomaly detection and domain risk scoring.
    """
    
    # Common ports for common_port_ratio calculation
    COMMON_PORTS = {80, 443, 22, 53, 25, 110, 143, 993, 995}
    
    # Common TLDs (for tld_category)
    COMMON_TLDS = {
        "com", "net", "org", "edu", "gov", "mil",
        "co", "io", "ai", "app", "dev"
    }
    
    SUSPICIOUS_TLDS = {
        "tk", "ml", "ga", "cf", "gq",  # Free TLDs often abused
        "top", "xyz", "club", "work", "date", "download"
    }
    
    @staticmethod
    def _parse_log_entry(entry: Dict) -> Optional[Dict]:
        """
        Parse a log entry from Loki.
        
        Args:
            entry: Log entry from Loki (with 'log' field containing JSON)
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            log_line = entry.get("log", "{}")
            return json.loads(log_line)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse log entry: {log_line[:100]}")
            return None
    
    @staticmethod
    def _calculate_entropy(s: str) -> float:
        """
        Calculate Shannon entropy of a string.
        
        Args:
            s: Input string
            
        Returns:
            Entropy value (0.0 to ~4.5 for typical domains)
        """
        if not s:
            return 0.0
        
        counter = Counter(s.lower())
        length = len(s)
        entropy = 0.0
        
        for count in counter.values():
            p = count / length
            entropy -= p * math.log2(p)
        
        return entropy
    
    @staticmethod
    def _categorize_tld(tld: str) -> str:
        """
        Categorize TLD as common, rare, or suspicious.
        
        Args:
            tld: Top-level domain (e.g., 'com', 'xyz')
            
        Returns:
            Category: 'common', 'rare', or 'suspicious'
        """
        tld = tld.lower()
        if tld in FeatureExtractor.COMMON_TLDS:
            return "common"
        elif tld in FeatureExtractor.SUSPICIOUS_TLDS:
            return "suspicious"
        else:
            return "rare"
    
    def extract_device_features(
        self,
        device_ip: str,
        flows: List[Dict],
        dns_queries: List[Dict],
        alerts: List[Dict],
        window_start: datetime,
        window_end: datetime
    ) -> DeviceFeatures:
        """
        Extract device-level features from logs.
        
        Args:
            device_ip: IP address of device
            flows: Suricata flow events
            dns_queries: DNS query events
            alerts: Suricata alert events
            window_start: Start of time window
            window_end: End of time window
            
        Returns:
            DeviceFeatures object
        """
        features = DeviceFeatures(
            device_ip=device_ip,
            window_start=window_start,
            window_end=window_end
        )
        
        # Parse flows
        parsed_flows = [self._parse_log_entry(f) for f in flows]
        parsed_flows = [f for f in parsed_flows if f is not None]
        
        if not parsed_flows:
            logger.debug(f"No flows found for device {device_ip}")
            return features
        
        # Connection counts
        features.connection_count_out = len(
            [f for f in parsed_flows if f.get("src_ip") == device_ip]
        )
        features.connection_count_in = len(
            [f for f in parsed_flows if f.get("dest_ip") == device_ip]
        )
        
        # Bytes
        features.bytes_sent = sum(
            f.get("flow", {}).get("bytes_toserver", 0)
            for f in parsed_flows if f.get("src_ip") == device_ip
        )
        features.bytes_received = sum(
            f.get("flow", {}).get("bytes_toclient", 0)
            for f in parsed_flows if f.get("src_ip") == device_ip
        )
        
        # Unique destinations
        dest_ips: Set[str] = set()
        dest_ports: Set[int] = set()
        protocols = []
        durations = []
        common_port_count = 0
        rare_port_count = 0
        
        for flow in parsed_flows:
            if flow.get("src_ip") == device_ip:
                dest_ips.add(flow.get("dest_ip", ""))
                dest_port = flow.get("dest_port", 0)
                dest_ports.add(dest_port)
                protocols.append(flow.get("proto", "").upper())
                
                # Duration
                flow_data = flow.get("flow", {})
                if "age" in flow_data:
                    durations.append(flow_data["age"])
                
                # Port analysis
                if dest_port in self.COMMON_PORTS:
                    common_port_count += 1
                elif dest_port > 1024:
                    rare_port_count += 1
        
        features.unique_dest_ips = len(dest_ips)
        features.unique_dest_ports = len(dest_ports)
        
        # Protocol distribution
        total_conns = len(protocols)
        if total_conns > 0:
            protocol_counts = Counter(protocols)
            features.protocol_tcp_ratio = protocol_counts.get("TCP", 0) / total_conns
            features.protocol_udp_ratio = protocol_counts.get("UDP", 0) / total_conns
            features.protocol_icmp_ratio = protocol_counts.get("ICMP", 0) / total_conns
            
            features.common_port_ratio = common_port_count / total_conns
        
        features.rare_port_count = rare_port_count
        
        # Timing
        if durations:
            features.avg_connection_duration = np.mean(durations)
        
        window_minutes = (window_end - window_start).total_seconds() / 60
        if window_minutes > 0:
            features.connection_rate_per_minute = total_conns / window_minutes
        
        # Data transfer
        if total_conns > 0:
            features.avg_bytes_per_connection = (
                (features.bytes_sent + features.bytes_received) / total_conns
            )
        
        if features.bytes_received > 0:
            features.upload_download_ratio = features.bytes_sent / features.bytes_received
        
        # DNS features
        parsed_dns = [self._parse_log_entry(d) for d in dns_queries]
        parsed_dns = [d for d in parsed_dns if d is not None]
        
        features.dns_query_count = len(parsed_dns)
        
        domains: Set[str] = set()
        domain_lengths = []
        domain_entropies = []
        nxdomain_count = 0
        
        for dns in parsed_dns:
            dns_data = dns.get("dns", {})
            if dns_data.get("type") == "query":
                domain = dns_data.get("rrname", "")
                if domain:
                    domains.add(domain)
                    domain_lengths.append(len(domain))
                    domain_entropies.append(self._calculate_entropy(domain))
            
            # Check for NXDOMAIN (failed lookups)
            if dns_data.get("rcode") == "NXDOMAIN":
                nxdomain_count += 1
        
        features.unique_domains = len(domains)
        if domain_lengths:
            features.avg_domain_length = np.mean(domain_lengths)
        if domain_entropies:
            features.avg_domain_entropy = np.mean(domain_entropies)
        if features.dns_query_count > 0:
            features.nxdomain_ratio = nxdomain_count / features.dns_query_count
        
        # Alert features
        parsed_alerts = [self._parse_log_entry(a) for a in alerts]
        parsed_alerts = [a for a in parsed_alerts if a is not None]
        
        features.alert_count = len(parsed_alerts)
        
        alert_sigs: Set[str] = set()
        for alert in parsed_alerts:
            alert_data = alert.get("alert", {})
            sig = alert_data.get("signature", "")
            if sig:
                alert_sigs.add(sig)
        
        features.unique_alert_signatures = len(alert_sigs)
        
        logger.debug(f"Extracted features for device {device_ip}: {features.to_dict()}")
        return features
    
    def extract_domain_features(self, domain: str, query_count: int = 0) -> DomainFeatures:
        """
        Extract domain-level features.
        
        Args:
            domain: Domain name (e.g., 'example.com')
            query_count: Number of times queried in time window
            
        Returns:
            DomainFeatures object
        """
        features = DomainFeatures(domain=domain, query_count=query_count)
        
        # Basic length features
        features.domain_length = len(domain)
        
        # Split domain into parts
        parts = domain.split(".")
        features.subdomain_count = len(parts) - 2 if len(parts) >= 2 else 0
        features.tld = parts[-1] if parts else ""
        features.tld_length = len(features.tld)
        features.tld_category = self._categorize_tld(features.tld)
        
        # Character analysis
        features.char_entropy = self._calculate_entropy(domain)
        
        domain_lower = domain.lower()
        vowels = set("aeiou")
        consonants = set("bcdfghjklmnpqrstvwxyz")
        hex_chars = set("0123456789abcdef")
        
        vowel_count = sum(1 for c in domain_lower if c in vowels)
        consonant_count = sum(1 for c in domain_lower if c in consonants)
        digit_count = sum(1 for c in domain_lower if c.isdigit())
        hex_count = sum(1 for c in domain_lower if c in hex_chars)
        
        total_alpha = vowel_count + consonant_count
        if total_alpha > 0:
            features.vowel_ratio = vowel_count / total_alpha
            features.consonant_ratio = consonant_count / total_alpha
        
        if len(domain) > 0:
            features.digit_ratio = digit_count / len(domain)
            features.hex_ratio = hex_count / len(domain)
        
        # Special characters (hyphens, underscores)
        features.special_char_count = domain.count("-") + domain.count("_")
        
        # IP pattern detection
        features.has_ip_pattern = any(
            part.isdigit() and 0 <= int(part) <= 255
            for part in domain.replace(".", " ").split()
            if part
        )
        
        # Max consonant streak (DGA domains often have long consonant sequences)
        max_streak = 0
        current_streak = 0
        for c in domain_lower:
            if c in consonants:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        features.max_consonant_streak = max_streak
        
        logger.debug(f"Extracted features for domain {domain}: {features.to_dict()}")
        return features

"""
Threat Intelligence Lookup Service

Provides fast IOC lookups for domains, IPs, and URLs.
"""

import logging
import os
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional

from orion_ai.threat_intel.ioc_models import IOC, IOCType, IntelSource
from orion_ai.threat_intel.store import IOCStore

logger = logging.getLogger(__name__)


class ThreatIntelLookup:
    """
    Fast threat intelligence lookup service.
    
    Provides lookup methods for domains, IPs, and URLs against the IOC store.
    """
    
    def __init__(self, store_path: Path = None):
        """
        Initialize threat intel lookup.
        
        Args:
            store_path: Path to IOC store database
        """
        if store_path is None:
            store_path = Path(os.getenv(
                "IOC_STORE_PATH",
                "/data/threat_intel.db"
            ))
        
        self.store = IOCStore(db_path=store_path)
        logger.info(f"Initialized ThreatIntelLookup with store at {store_path}")
    
    def lookup_domain(self, domain: str) -> Optional[Dict]:
        """
        Lookup a domain in threat intel.
        
        Args:
            domain: Domain name to lookup
            
        Returns:
            Dict with IOC info if found, None otherwise
        """
        result = self.store.lookup(IOCType.DOMAIN, domain.lower())
        
        if result:
            ioc_id, confidence, source = result
            return {
                "ioc_id": ioc_id,
                "value": domain,
                "type": "domain",
                "source": source,
                "confidence": confidence,
            }
        
        return None
    
    def lookup_ip(self, ip: str) -> Optional[Dict]:
        """
        Lookup an IP address in threat intel.
        
        Args:
            ip: IP address to lookup
            
        Returns:
            Dict with IOC info if found, None otherwise
        """
        result = self.store.lookup(IOCType.IP, ip)
        
        if result:
            ioc_id, confidence, source = result
            return {
                "ioc_id": ioc_id,
                "value": ip,
                "type": "ip",
                "source": source,
                "confidence": confidence,
            }
        
        return None
    
    def lookup_url(self, url: str) -> Optional[Dict]:
        """
        Lookup a URL in threat intel.
        
        Args:
            url: URL to lookup
            
        Returns:
            Dict with IOC info if found, None otherwise
        """
        result = self.store.lookup(IOCType.URL, url.lower())
        
        if result:
            ioc_id, confidence, source = result
            return {
                "ioc_id": ioc_id,
                "value": url,
                "type": "url",
                "source": source,
                "confidence": confidence,
            }
        
        return None
    
    def bulk_lookup_domains(self, domains: Set[str]) -> Dict[str, Dict]:
        """
        Bulk lookup multiple domains.
        
        Args:
            domains: Set of domain names
            
        Returns:
            Dict mapping domain -> IOC info
        """
        if not domains:
            return {}
        
        results = self.store.bulk_lookup(IOCType.DOMAIN, domains)
        
        # Convert to more usable format
        # Create reverse mapping for case-insensitive match
        domain_lower_map = {d.lower(): d for d in domains}
        
        matches = {}
        for domain_lower, (ioc_id, confidence, source) in results.items():
            # Get original domain (case-preserved)
            original_domain = domain_lower_map.get(domain_lower, domain_lower)
            matches[original_domain] = {
                "ioc_id": ioc_id,
                "value": original_domain,
                "type": "domain",
                "source": source,
                "confidence": confidence,
            }
        
        return matches
    
    def bulk_lookup_ips(self, ips: Set[str]) -> Dict[str, Dict]:
        """
        Bulk lookup multiple IP addresses.
        
        Args:
            ips: Set of IP addresses
            
        Returns:
            Dict mapping IP -> IOC info
        """
        if not ips:
            return {}
        
        results = self.store.bulk_lookup(IOCType.IP, ips)
        
        matches = {}
        for ip, (ioc_id, confidence, source) in results.items():
            matches[ip] = {
                "ioc_id": ioc_id,
                "value": ip,
                "type": "ip",
                "source": source,
                "confidence": confidence,
            }
        
        return matches
    
    def record_match(
        self,
        ioc_id: int,
        log_type: str,
        matched_value: str,
        context: Optional[str] = None
    ) -> None:
        """
        Record that an IOC was matched in logs.
        
        Args:
            ioc_id: IOC database ID
            log_type: Type of log (e.g., "dns", "suricata", "http")
            matched_value: The value that matched
            context: Optional context from the log
        """
        self.store.record_match(
            ioc_id=ioc_id,
            log_type=log_type,
            matched_value=matched_value,
            context=context
        )


# Global instance
_ti_lookup: Optional[ThreatIntelLookup] = None


def get_ti_lookup() -> ThreatIntelLookup:
    """
    Get or create global ThreatIntelLookup instance.
    
    Returns:
        ThreatIntelLookup instance
    """
    global _ti_lookup
    if _ti_lookup is None:
        _ti_lookup = ThreatIntelLookup()
    return _ti_lookup


def enrich_event_with_ti(event_data: Dict, ti_lookup: ThreatIntelLookup = None) -> Dict:
    """
    Enrich an event with threat intelligence context.
    
    Looks up domains/IPs in the event and adds TI matches to metadata.
    
    Args:
        event_data: Event dictionary
        ti_lookup: Optional TI lookup instance (uses global if None)
        
    Returns:
        Enriched event data with TI context
    """
    if ti_lookup is None:
        ti_lookup = get_ti_lookup()
    
    metadata = event_data.get("metadata", {})
    
    # Extract domains and IPs to lookup
    domains_to_check = set()
    ips_to_check = set()
    
    # Check metadata for domain/IP fields
    if "domain" in metadata:
        domains_to_check.add(metadata["domain"])
    if "ip" in metadata:
        ips_to_check.add(metadata["ip"])
    if "dest_ip" in metadata:
        ips_to_check.add(metadata["dest_ip"])
    if "src_ip" in metadata:
        ips_to_check.add(metadata["src_ip"])
    
    # Check top-level fields
    if "ip" in event_data:
        ips_to_check.add(event_data["ip"])
    
    # Perform lookups
    ioc_matches = []
    ti_sources = set()
    
    # Lookup domains
    if domains_to_check:
        domain_matches = ti_lookup.bulk_lookup_domains(domains_to_check)
        for domain, match_info in domain_matches.items():
            ioc_matches.append({
                "type": "domain",
                "value": domain,
                "source": match_info["source"],
                "confidence": match_info["confidence"],
            })
            ti_sources.add(match_info["source"])
            
            # Record the match
            ti_lookup.record_match(
                ioc_id=match_info["ioc_id"],
                log_type=event_data.get("event_type", "unknown"),
                matched_value=domain,
                context=event_data.get("title", "")
            )
    
    # Lookup IPs
    if ips_to_check:
        ip_matches = ti_lookup.bulk_lookup_ips(ips_to_check)
        for ip, match_info in ip_matches.items():
            ioc_matches.append({
                "type": "ip",
                "value": ip,
                "source": match_info["source"],
                "confidence": match_info["confidence"],
            })
            ti_sources.add(match_info["source"])
            
            # Record the match
            ti_lookup.record_match(
                ioc_id=match_info["ioc_id"],
                log_type=event_data.get("event_type", "unknown"),
                matched_value=ip,
                context=event_data.get("title", "")
            )
    
    # Add TI context to event metadata
    if ioc_matches:
        metadata["ioc_matches"] = ioc_matches
        metadata["ti_sources"] = list(ti_sources)
        metadata["ti_matched"] = True
        
        # Add human-readable reasons
        reasons = metadata.get("reasons", [])
        for match in ioc_matches:
            reasons.append(
                f"Matched {match['type']} {match['value']} "
                f"in {match['source']} (confidence: {match['confidence']:.2f})"
            )
        metadata["reasons"] = reasons
        
        # Boost risk score if present
        if "risk_score" in metadata:
            # Add boost based on confidence
            max_confidence = max(m["confidence"] for m in ioc_matches)
            boost = max_confidence * 0.3  # Up to 0.3 boost
            metadata["risk_score"] = min(1.0, metadata["risk_score"] + boost)
            metadata["ti_boost"] = boost
        
        event_data["metadata"] = metadata
        
        logger.info(
            f"Enriched event {event_data.get('event_id', 'unknown')} "
            f"with {len(ioc_matches)} TI matches"
        )
    
    return event_data

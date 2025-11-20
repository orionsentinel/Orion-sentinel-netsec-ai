"""
Device fingerprinting and type detection.
"""

import logging
from typing import List, Optional

from .models import Device

logger = logging.getLogger(__name__)


class DeviceFingerprinter:
    """
    Fingerprints devices to guess their type based on network behavior.
    
    Uses heuristics like:
    - Port patterns
    - Destination patterns
    - MAC vendor
    - Traffic patterns
    """

    # Port fingerprints for common device types
    PORT_FINGERPRINTS = {
        "Chromecast/Google TV": [8008, 8009, 8443],
        "Apple TV": [3689, 5000, 7000],
        "Smart TV": [8001, 8002, 9197],
        "Printer": [631, 9100, 515],
        "NAS": [445, 139, 548, 2049, 5000, 5001],
        "IP Camera": [554, 8000, 8080],
        "Smart Speaker": [8009, 55443],
    }

    # Destination domain patterns
    DOMAIN_FINGERPRINTS = {
        "Chromecast/Google TV": ["googleusercontent.com", "googleapis.com", "gvt1.com"],
        "Apple Device": ["apple.com", "icloud.com", "mzstatic.com"],
        "Amazon Device": ["amazon.com", "amazonaws.com", "cloudfront.net"],
        "Smart TV": ["smart-tv-", "tv."],
        "IoT Device": ["iot.", "device."],
    }

    # MAC vendor prefixes (first 3 octets)
    VENDOR_FINGERPRINTS = {
        "Google": ["Google", "Chromecast"],
        "Apple": ["Apple Device", "iPhone", "iPad", "Mac"],
        "Samsung": ["Smart TV", "Samsung Device"],
        "Amazon": ["Amazon Device", "Echo"],
        "Raspberry Pi": ["Raspberry Pi", "IoT"],
    }

    def fingerprint_device(self, device: Device) -> Device:
        """
        Analyze device and update its type guess.
        
        Args:
            device: Device to fingerprint
            
        Returns:
            Updated device with guess_type set
        """
        guesses: List[str] = []
        
        # Check port patterns
        port_guess = self._guess_from_ports(device.open_ports)
        if port_guess:
            guesses.append(port_guess)
        
        # Check destination patterns
        dest_guess = self._guess_from_destinations(device.common_destinations)
        if dest_guess:
            guesses.append(dest_guess)
        
        # Check vendor
        vendor_guess = self._guess_from_vendor(device.vendor)
        if vendor_guess:
            guesses.append(vendor_guess)
        
        # Pick most specific guess
        if guesses:
            # TODO: Implement better consensus logic
            device.guess_type = guesses[0]
        else:
            device.guess_type = "unknown"
        
        logger.debug(f"Fingerprinted {device.ip}: {device.guess_type} (guesses: {guesses})")
        
        return device

    def _guess_from_ports(self, open_ports: List[int]) -> Optional[str]:
        """
        Guess device type from open ports.
        
        Args:
            open_ports: List of open ports
            
        Returns:
            Device type guess or None
        """
        if not open_ports:
            return None
        
        port_set = set(open_ports)
        best_match = None
        best_match_score = 0
        
        for device_type, fingerprint_ports in self.PORT_FINGERPRINTS.items():
            fingerprint_set = set(fingerprint_ports)
            matches = len(port_set & fingerprint_set)
            
            if matches > best_match_score:
                best_match_score = matches
                best_match = device_type
        
        return best_match if best_match_score >= 2 else None

    def _guess_from_destinations(self, destinations: List[str]) -> Optional[str]:
        """
        Guess device type from common destinations.
        
        Args:
            destinations: List of common destination domains
            
        Returns:
            Device type guess or None
        """
        if not destinations:
            return None
        
        for device_type, patterns in self.DOMAIN_FINGERPRINTS.items():
            for dest in destinations:
                for pattern in patterns:
                    if pattern in dest:
                        return device_type
        
        return None

    def _guess_from_vendor(self, vendor: Optional[str]) -> Optional[str]:
        """
        Guess device type from vendor.
        
        Args:
            vendor: MAC vendor string
            
        Returns:
            Device type guess or None
        """
        if not vendor:
            return None
        
        vendor_lower = vendor.lower()
        
        for vendor_key, types in self.VENDOR_FINGERPRINTS.items():
            if vendor_key.lower() in vendor_lower:
                return types[0] if types else None
        
        return None

    def suggest_tags(self, device: Device) -> List[str]:
        """
        Suggest tags for a device based on its fingerprint.
        
        Args:
            device: Device to tag
            
        Returns:
            List of suggested tags
        """
        tags = []
        
        # Type-based tags
        if device.guess_type:
            type_lower = device.guess_type.lower()
            
            if any(x in type_lower for x in ["tv", "chromecast", "apple tv"]):
                tags.append("media")
                tags.append("iot")
            elif "camera" in type_lower:
                tags.append("security")
                tags.append("iot")
            elif "printer" in type_lower:
                tags.append("office")
            elif "nas" in type_lower:
                tags.append("storage")
                tags.append("server")
            elif any(x in type_lower for x in ["speaker", "echo", "alexa"]):
                tags.append("smart-home")
                tags.append("iot")
            elif "phone" in type_lower or "mobile" in type_lower:
                tags.append("mobile")
            elif "raspberry" in type_lower:
                tags.append("lab")
                tags.append("iot")
        
        # Risk-based tags
        if device.risk_score > 0.7:
            tags.append("high-risk")
        elif device.risk_score > 0.4:
            tags.append("medium-risk")
        
        # Activity-based tags
        if device.anomaly_count > 5:
            tags.append("anomalous")
        
        if device.intel_match_count > 0:
            tags.append("threat-indicator")
        
        return tags

"""
Orion Sentinel Wizard - Configuration Views

Logic for reading/writing configuration files.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

import httpx
from pydantic import BaseModel, Field


class WizardConfig(BaseModel):
    """Configuration collected from the wizard."""
    
    # DNS Pi settings
    dns_pi_ip: str = Field(default="192.168.1.10", description="IP address of DNS Pi (Pi #1)")
    pihole_enabled: bool = Field(default=False, description="Whether Pi-hole API is enabled")
    pihole_api_token: Optional[str] = Field(default=None, description="Pi-hole API token")
    
    # Network settings
    nsm_iface: str = Field(default="eth0", description="Network interface for monitoring")
    operating_mode: str = Field(
        default="observe",
        description="Operating mode: observe, alert, or safe_block"
    )
    
    # Feature flags
    enable_ai: bool = Field(default=False, description="Enable AI anomaly detection")
    enable_intel: bool = Field(default=False, description="Enable threat intelligence")


# Path to setup completion marker
SETUP_DONE_FILE = Path("/tmp/.orion_setup_done")

# Config file paths
NSM_ENV_FILE = Path("/app/stacks/nsm/.env")
AI_ENV_FILE = Path("/app/stacks/ai/.env")

# For dev/testing, allow override
if os.getenv("ORION_DEV_MODE"):
    SETUP_DONE_FILE = Path("/tmp/.orion_setup_done")
    NSM_ENV_FILE = Path("/tmp/nsm.env")
    AI_ENV_FILE = Path("/tmp/ai.env")


def check_setup_done() -> bool:
    """
    Check if initial setup has been completed.
    """
    return SETUP_DONE_FILE.exists()


def mark_setup_done() -> None:
    """
    Mark setup as completed.
    """
    SETUP_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETUP_DONE_FILE.touch()


def test_pihole_connection(ip: str, token: str) -> Tuple[bool, str]:
    """
    Test connection to Pi-hole API.
    
    Args:
        ip: IP address of Pi-hole instance
        token: API token
    
    Returns:
        Tuple of (success, message)
    """
    # Validate IP address format to prevent SSRF
    import re
    ip_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    if not ip_pattern.match(ip):
        return False, "Invalid IP address format"
    
    # Additional validation: ensure octets are in valid range
    try:
        octets = [int(octet) for octet in ip.split(".")]
        if any(octet < 0 or octet > 255 for octet in octets):
            return False, "IP address octets must be between 0 and 255"
    except ValueError:
        return False, "Invalid IP address"
    
    # Prevent access to localhost/loopback unless explicitly allowed
    if ip.startswith("127.") or ip.startswith("0."):
        return False, "Cannot connect to loopback addresses"
    
    try:
        url = f"http://{ip}/admin/api.php"
        params = {
            "auth": token,
            "status": ""
        }
        
        response = httpx.get(url, params=params, timeout=5.0)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "enabled":
                return True, "Pi-hole connection successful"
            else:
                return False, f"Unexpected status: {data.get('status')}"
        else:
            return False, f"HTTP {response.status_code}"
    
    except httpx.TimeoutException:
        return False, "Connection timeout - check IP address"
    except httpx.ConnectError:
        return False, "Cannot connect - check IP address and network"
    except Exception as e:
        return False, f"Error: {str(e)}"


def update_env_file(file_path: Path, updates: dict) -> None:
    """
    Update values in a .env file.
    
    Args:
        file_path: Path to .env file
        updates: Dictionary of key-value pairs to update
    """
    # Read existing content
    if file_path.exists():
        lines = file_path.read_text().splitlines()
    else:
        lines = []
    
    # Update or append values
    updated_keys = set()
    new_lines = []
    
    for line in lines:
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            new_lines.append(line)
            continue
        
        # Parse key=value
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Add any keys that weren't already in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")
    
    # Write back
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(new_lines) + "\n")


def apply_configuration(config: WizardConfig) -> Tuple[bool, str]:
    """
    Apply wizard configuration to system files.
    
    Args:
        config: WizardConfig object with settings
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Update NSM stack configuration
        nsm_updates = {
            "NSM_IFACE": config.nsm_iface,
        }
        
        if NSM_ENV_FILE.parent.exists() or os.getenv("ORION_DEV_MODE"):
            update_env_file(NSM_ENV_FILE, nsm_updates)
        
        # Update AI stack configuration
        ai_updates = {}
        
        if config.pihole_enabled and config.pihole_api_token:
            ai_updates["PIHOLE_API_URL"] = f"http://{config.dns_pi_ip}/admin/api.php"
            ai_updates["PIHOLE_API_TOKEN"] = config.pihole_api_token
        
        # Set mode
        if config.operating_mode == "observe":
            ai_updates["ENABLE_BLOCKING"] = "false"
            ai_updates["SOAR_DRY_RUN"] = "1"
        elif config.operating_mode == "alert":
            ai_updates["ENABLE_BLOCKING"] = "false"
            ai_updates["SOAR_DRY_RUN"] = "0"
        elif config.operating_mode == "safe_block":
            ai_updates["ENABLE_BLOCKING"] = "true"
            ai_updates["SOAR_DRY_RUN"] = "0"
        
        # Feature flags
        ai_updates["THREAT_INTEL_ENABLE"] = "true" if config.enable_intel else "false"
        
        if AI_ENV_FILE.parent.exists() or os.getenv("ORION_DEV_MODE"):
            update_env_file(AI_ENV_FILE, ai_updates)
        
        # Create a config summary
        summary_lines = [
            "Orion Sentinel Configuration Applied",
            f"DNS Pi IP: {config.dns_pi_ip}",
            f"NSM Interface: {config.nsm_iface}",
            f"Operating Mode: {config.operating_mode}",
            f"AI Detection: {'Enabled' if config.enable_ai else 'Disabled'}",
            f"Threat Intel: {'Enabled' if config.enable_intel else 'Disabled'}",
        ]
        
        return True, "\n".join(summary_lines)
    
    except Exception as e:
        return False, f"Configuration failed: {str(e)}"


def get_local_ip() -> str:
    """
    Get the local IP address of this system.
    
    Returns:
        IP address as string, or 'localhost' if cannot determine
    """
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            return ip
        finally:
            s.close()
    except Exception:
        return "localhost"

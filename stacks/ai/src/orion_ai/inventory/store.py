"""
Device store for persisting device inventory.

Uses SQLite for lightweight persistence of device metadata.
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from orion_ai.core.models import Device

logger = logging.getLogger(__name__)


class DeviceStore:
    """
    SQLite-based storage for device inventory.
    
    Provides CRUD operations for Device objects.
    """
    
    def __init__(self, db_path: str = "/var/lib/orion-ai/devices.db"):
        """
        Initialize device store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Initialized DeviceStore at {db_path}")
    
    def _init_db(self) -> None:
        """Create database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    ip TEXT NOT NULL,
                    mac TEXT,
                    hostname TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    tags TEXT,
                    guess_type TEXT,
                    owner TEXT
                )
            """)
            
            # Create indices for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_ip 
                ON devices(ip)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_mac 
                ON devices(mac)
            """)
            
            conn.commit()
    
    def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """
        Get device by its unique ID.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE device_id = ?",
                (device_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_device(row)
            return None
    
    def get_device_by_ip(self, ip: str) -> Optional[Device]:
        """
        Get device by IP address.
        
        Args:
            ip: IP address
            
        Returns:
            Device if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE ip = ? ORDER BY last_seen DESC LIMIT 1",
                (ip,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_device(row)
            return None
    
    def get_device_by_mac(self, mac: str) -> Optional[Device]:
        """
        Get device by MAC address.
        
        Args:
            mac: MAC address
            
        Returns:
            Device if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE mac = ? ORDER BY last_seen DESC LIMIT 1",
                (mac,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_device(row)
            return None
    
    def list_devices(
        self,
        tag_filter: Optional[str] = None,
        limit: int = 1000
    ) -> List[Device]:
        """
        List all devices, optionally filtered by tag.
        
        Args:
            tag_filter: Optional tag to filter by
            limit: Maximum number of devices to return
            
        Returns:
            List of Device objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if tag_filter:
                # Filter by tag (tags stored as JSON array)
                cursor = conn.execute(
                    "SELECT * FROM devices WHERE tags LIKE ? ORDER BY last_seen DESC LIMIT ?",
                    (f'%"{tag_filter}"%', limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM devices ORDER BY last_seen DESC LIMIT ?",
                    (limit,)
                )
            
            return [self._row_to_device(row) for row in cursor.fetchall()]
    
    def upsert_device(self, device: Device) -> None:
        """
        Insert or update a device.
        
        Args:
            device: Device object to store
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO devices (
                    device_id, ip, mac, hostname, 
                    first_seen, last_seen, tags, guess_type, owner
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    ip = excluded.ip,
                    mac = COALESCE(excluded.mac, devices.mac),
                    hostname = COALESCE(excluded.hostname, devices.hostname),
                    last_seen = excluded.last_seen,
                    tags = excluded.tags,
                    guess_type = COALESCE(excluded.guess_type, devices.guess_type),
                    owner = COALESCE(excluded.owner, devices.owner)
            """, (
                device.device_id,
                device.ip,
                device.mac,
                device.hostname,
                device.first_seen.isoformat(),
                device.last_seen.isoformat(),
                json.dumps(device.tags),
                device.guess_type,
                device.owner
            ))
            conn.commit()
        
        logger.debug(f"Upserted device: {device.device_id} ({device.ip})")
    
    def tag_device(self, device_id: str, tag: str) -> bool:
        """
        Add a tag to a device.
        
        Args:
            device_id: Device identifier
            tag: Tag to add
            
        Returns:
            True if successful, False if device not found
        """
        device = self.get_device_by_id(device_id)
        if not device:
            return False
        
        if tag not in device.tags:
            device.tags.append(tag)
            self.upsert_device(device)
            logger.info(f"Added tag '{tag}' to device {device_id}")
        
        return True
    
    def untag_device(self, device_id: str, tag: str) -> bool:
        """
        Remove a tag from a device.
        
        Args:
            device_id: Device identifier
            tag: Tag to remove
            
        Returns:
            True if successful, False if device not found
        """
        device = self.get_device_by_id(device_id)
        if not device:
            return False
        
        if tag in device.tags:
            device.tags.remove(tag)
            self.upsert_device(device)
            logger.info(f"Removed tag '{tag}' from device {device_id}")
        
        return True
    
    def delete_device(self, device_id: str) -> bool:
        """
        Delete a device from the store.
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM devices WHERE device_id = ?",
                (device_id,)
            )
            conn.commit()
            
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted device: {device_id}")
            
            return deleted
    
    def _row_to_device(self, row: sqlite3.Row) -> Device:
        """Convert database row to Device object."""
        return Device(
            device_id=row["device_id"],
            ip=row["ip"],
            mac=row["mac"],
            hostname=row["hostname"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            guess_type=row["guess_type"],
            owner=row["owner"]
        )
    
    @staticmethod
    def generate_device_id(ip: str, mac: Optional[str] = None) -> str:
        """
        Generate a deterministic device ID from IP and MAC.
        
        Args:
            ip: IP address
            mac: Optional MAC address
            
        Returns:
            Stable device identifier
        """
        # Use MAC if available for stability, otherwise use IP
        key = mac if mac else ip
        return hashlib.sha256(key.encode()).hexdigest()[:16]

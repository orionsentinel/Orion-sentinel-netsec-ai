"""
Device inventory persistent storage.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import Device

logger = logging.getLogger(__name__)


class InventoryStore:
    """
    Persistent storage for device inventory using SQLite.
    
    Provides CRUD operations for devices.
    """

    def __init__(self, db_path: str = "/data/inventory.db"):
        """
        Initialize inventory store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    ip TEXT PRIMARY KEY,
                    mac TEXT,
                    hostname TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    tags TEXT,
                    guess_type TEXT,
                    owner TEXT,
                    vendor TEXT,
                    os_guess TEXT,
                    open_ports TEXT,
                    common_destinations TEXT,
                    risk_score REAL DEFAULT 0.0,
                    anomaly_count INTEGER DEFAULT 0,
                    intel_match_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON devices(last_seen)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON devices(tags)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_score ON devices(risk_score)")
            
            conn.commit()
        
        logger.info(f"Initialized inventory database at {self.db_path}")

    def get_device(self, ip: str) -> Optional[Device]:
        """
        Get device by IP address.
        
        Args:
            ip: IP address
            
        Returns:
            Device or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM devices WHERE ip = ?", (ip,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_device(dict(row))

    def upsert_device(self, device: Device) -> None:
        """
        Insert or update device.
        
        Args:
            device: Device to save
        """
        device_dict = device.dict()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO devices (
                    ip, mac, hostname, first_seen, last_seen, tags, guess_type,
                    owner, vendor, os_guess, open_ports, common_destinations,
                    risk_score, anomaly_count, intel_match_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device.ip,
                    device.mac,
                    device.hostname,
                    device.first_seen.isoformat(),
                    device.last_seen.isoformat(),
                    json.dumps(device.tags),
                    device.guess_type,
                    device.owner,
                    device.vendor,
                    device.os_guess,
                    json.dumps(device.open_ports),
                    json.dumps(device.common_destinations),
                    device.risk_score,
                    device.anomaly_count,
                    device.intel_match_count,
                ),
            )
            conn.commit()
        
        logger.debug(f"Saved device: {device.ip}")

    def list_devices(
        self, tags: Optional[List[str]] = None, limit: Optional[int] = None
    ) -> List[Device]:
        """
        List devices with optional filtering.
        
        Args:
            tags: Filter by tags (OR logic)
            limit: Maximum number of devices to return
            
        Returns:
            List of devices
        """
        query = "SELECT * FROM devices"
        params = []
        
        # TODO: Implement tag filtering (requires JSON support or normalization)
        
        query += " ORDER BY last_seen DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_device(dict(row)) for row in rows]

    def list_new_devices_since(self, since: datetime) -> List[Device]:
        """
        List devices first seen since a given time.
        
        Args:
            since: Datetime threshold
            
        Returns:
            List of new devices
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE first_seen >= ? ORDER BY first_seen DESC",
                (since.isoformat(),),
            )
            rows = cursor.fetchall()
            
            return [self._row_to_device(dict(row)) for row in rows]

    def tag_device(self, ip: str, tag: str) -> bool:
        """
        Add a tag to a device.
        
        Args:
            ip: Device IP
            tag: Tag to add
            
        Returns:
            True if successful
        """
        device = self.get_device(ip)
        if not device:
            logger.warning(f"Device {ip} not found for tagging")
            return False
        
        if tag not in device.tags:
            device.tags.append(tag)
            self.upsert_device(device)
            logger.info(f"Tagged device {ip} with '{tag}'")
        
        return True

    def _row_to_device(self, row: Dict) -> Device:
        """Convert database row to Device model."""
        return Device(
            ip=row["ip"],
            mac=row["mac"],
            hostname=row["hostname"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            guess_type=row["guess_type"],
            owner=row["owner"],
            vendor=row["vendor"],
            os_guess=row["os_guess"],
            open_ports=json.loads(row["open_ports"]) if row["open_ports"] else [],
            common_destinations=json.loads(row["common_destinations"])
            if row["common_destinations"]
            else [],
            risk_score=row["risk_score"] or 0.0,
            anomaly_count=row["anomaly_count"] or 0,
            intel_match_count=row["intel_match_count"] or 0,
        )

    def get_stats(self) -> Dict:
        """Get inventory statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM devices")
            total = cursor.fetchone()[0]
            
            cursor = conn.execute(
                "SELECT COUNT(*) as high_risk FROM devices WHERE risk_score > 0.7"
            )
            high_risk = cursor.fetchone()[0]
            
            cursor = conn.execute(
                "SELECT COUNT(*) as unknown FROM devices WHERE guess_type IS NULL OR guess_type = 'unknown'"
            )
            unknown = cursor.fetchone()[0]
            
            return {
                "total_devices": total,
                "high_risk_devices": high_risk,
                "unknown_devices": unknown,
            }

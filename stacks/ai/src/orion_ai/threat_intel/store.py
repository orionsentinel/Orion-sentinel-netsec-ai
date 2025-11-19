"""
IOC Store

Persistent storage for Indicators of Compromise using SQLite.
Provides fast lookups and deduplication.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set, Tuple
from contextlib import contextmanager

from .ioc_extractor import IOC, IOCType

logger = logging.getLogger(__name__)


class IOCStore:
    """
    SQLite-based storage for IOCs.
    
    Features:
    - Fast lookups with indexes
    - Automatic deduplication
    - Expiration of old IOCs
    - Source attribution
    - Confidence tracking
    """
    
    def __init__(self, db_path: Path, retention_days: int = 90):
        """
        Initialize IOC store.
        
        Args:
            db_path: Path to SQLite database file
            retention_days: How long to keep IOCs (default: 90 days)
        """
        self.db_path = Path(db_path)
        self.retention_days = retention_days
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Initialized IOC store at {db_path}")
    
    def _init_db(self):
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS iocs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source TEXT NOT NULL,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    confidence REAL NOT NULL,
                    context TEXT,
                    hit_count INTEGER DEFAULT 0,
                    UNIQUE(type, value)
                )
            """)
            
            # Create indexes for fast lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ioc_type_value 
                ON iocs(type, value)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ioc_last_seen 
                ON iocs(last_seen)
            """)
            
            # Create table for IOC matches
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ioc_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ioc_id INTEGER NOT NULL,
                    matched_at TIMESTAMP NOT NULL,
                    log_type TEXT NOT NULL,
                    matched_value TEXT NOT NULL,
                    context TEXT,
                    FOREIGN KEY(ioc_id) REFERENCES iocs(id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_timestamp 
                ON ioc_matches(matched_at)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def add_iocs(self, iocs: List[IOC]) -> int:
        """
        Add IOCs to store.
        
        Deduplicates and updates existing IOCs.
        
        Args:
            iocs: List of IOC objects
            
        Returns:
            Number of IOCs added/updated
        """
        if not iocs:
            return 0
        
        now = datetime.now()
        count = 0
        
        with self._get_connection() as conn:
            for ioc in iocs:
                try:
                    conn.execute("""
                        INSERT INTO iocs 
                        (type, value, source, first_seen, last_seen, confidence, context)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(type, value) DO UPDATE SET
                            last_seen = ?,
                            confidence = MAX(confidence, ?),
                            context = COALESCE(?, context),
                            source = source || ',' || ?
                    """, (
                        ioc.type.value,
                        ioc.value,
                        ioc.source,
                        now,
                        now,
                        ioc.confidence,
                        ioc.context,
                        now,
                        ioc.confidence,
                        ioc.context,
                        ioc.source
                    ))
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to add IOC {ioc.value}: {e}")
            
            conn.commit()
        
        logger.info(f"Added/updated {count} IOCs to store")
        return count
    
    def lookup(
        self,
        ioc_type: IOCType,
        value: str
    ) -> Optional[Tuple[int, float, str]]:
        """
        Lookup IOC in store.
        
        Args:
            ioc_type: IOC type
            value: IOC value
            
        Returns:
            Tuple of (ioc_id, confidence, source) if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, confidence, source
                FROM iocs
                WHERE type = ? AND value = ?
                LIMIT 1
            """, (ioc_type.value, value.lower()))
            
            row = cursor.fetchone()
            if row:
                return (row['id'], row['confidence'], row['source'])
        
        return None
    
    def bulk_lookup(
        self,
        ioc_type: IOCType,
        values: Set[str]
    ) -> Dict[str, Tuple[int, float, str]]:
        """
        Bulk lookup multiple IOCs.
        
        Args:
            ioc_type: IOC type
            values: Set of IOC values
            
        Returns:
            Dict mapping value -> (ioc_id, confidence, source)
        """
        if not values:
            return {}
        
        results = {}
        
        # Normalize values
        values_lower = {v.lower() for v in values}
        
        with self._get_connection() as conn:
            # Build query with placeholders
            placeholders = ','.join('?' * len(values_lower))
            query = f"""
                SELECT value, id, confidence, source
                FROM iocs
                WHERE type = ? AND value IN ({placeholders})
            """
            
            cursor = conn.execute(
                query,
                [ioc_type.value] + list(values_lower)
            )
            
            for row in cursor:
                results[row['value']] = (
                    row['id'],
                    row['confidence'],
                    row['source']
                )
        
        return results
    
    def record_match(
        self,
        ioc_id: int,
        log_type: str,
        matched_value: str,
        context: Optional[str] = None
    ):
        """
        Record an IOC match in logs.
        
        Args:
            ioc_id: IOC database ID
            log_type: Type of log (suricata, dns, etc.)
            matched_value: The actual value that matched
            context: Optional context from log
        """
        now = datetime.now()
        
        with self._get_connection() as conn:
            # Insert match record
            conn.execute("""
                INSERT INTO ioc_matches
                (ioc_id, matched_at, log_type, matched_value, context)
                VALUES (?, ?, ?, ?, ?)
            """, (ioc_id, now, log_type, matched_value, context))
            
            # Increment hit count
            conn.execute("""
                UPDATE iocs
                SET hit_count = hit_count + 1
                WHERE id = ?
            """, (ioc_id,))
            
            conn.commit()
    
    def cleanup_old_iocs(self) -> int:
        """
        Remove IOCs older than retention period.
        
        Returns:
            Number of IOCs removed
        """
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM iocs
                WHERE last_seen < ?
            """, (cutoff,))
            
            count = cursor.rowcount
            conn.commit()
        
        if count > 0:
            logger.info(f"Cleaned up {count} old IOCs")
        
        return count
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get store statistics.
        
        Returns:
            Dict with IOC counts by type and total matches
        """
        stats = {}
        
        with self._get_connection() as conn:
            # Count by type
            cursor = conn.execute("""
                SELECT type, COUNT(*) as count
                FROM iocs
                GROUP BY type
            """)
            
            for row in cursor:
                stats[row['type']] = row['count']
            
            # Total IOCs
            cursor = conn.execute("SELECT COUNT(*) as count FROM iocs")
            stats['total'] = cursor.fetchone()['count']
            
            # Total matches
            cursor = conn.execute("SELECT COUNT(*) as count FROM ioc_matches")
            stats['total_matches'] = cursor.fetchone()['count']
            
            # Matches in last 24h
            yesterday = datetime.now() - timedelta(days=1)
            cursor = conn.execute("""
                SELECT COUNT(*) as count
                FROM ioc_matches
                WHERE matched_at > ?
            """, (yesterday,))
            stats['matches_24h'] = cursor.fetchone()['count']
        
        return stats
    
    def get_recent_matches(self, limit: int = 100) -> List[Dict]:
        """
        Get recent IOC matches.
        
        Args:
            limit: Maximum number of matches to return
            
        Returns:
            List of match dictionaries
        """
        matches = []
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    m.matched_at,
                    m.log_type,
                    m.matched_value,
                    m.context,
                    i.type,
                    i.value,
                    i.source,
                    i.confidence
                FROM ioc_matches m
                JOIN iocs i ON m.ioc_id = i.id
                ORDER BY m.matched_at DESC
                LIMIT ?
            """, (limit,))
            
            for row in cursor:
                matches.append({
                    'matched_at': row['matched_at'],
                    'log_type': row['log_type'],
                    'matched_value': row['matched_value'],
                    'context': row['context'],
                    'ioc_type': row['type'],
                    'ioc_value': row['value'],
                    'ioc_source': row['source'],
                    'confidence': row['confidence']
                })
        
        return matches

"""
Threat Intelligence Sync Service

CLI tool and service for fetching and syncing threat intelligence feeds.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from orion_ai.threat_intel.ioc_fetchers import (
    AlienVaultOTXFetcher,
    URLhausFetcher,
    FeodoTrackerFetcher,
    PhishTankFetcher,
)
from orion_ai.threat_intel.ioc_models import IOC
from orion_ai.threat_intel.store import IOCStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ThreatIntelSync:
    """
    Syncs threat intelligence from multiple feeds to local IOC store.
    """
    
    def __init__(self, store_path: Path = None):
        """
        Initialize threat intel sync.
        
        Args:
            store_path: Path to IOC store database
        """
        if store_path is None:
            store_path = Path(os.getenv(
                "IOC_STORE_PATH",
                "/data/threat_intel.db"
            ))
        
        self.store = IOCStore(db_path=store_path)
        
        # Initialize fetchers based on environment
        self.fetchers = self._init_fetchers()
    
    def _init_fetchers(self) -> dict:
        """Initialize enabled fetchers from environment variables."""
        fetchers = {}
        
        # AlienVault OTX (requires API key)
        otx_key = os.getenv("TI_OTX_API_KEY")
        if otx_key and os.getenv("TI_ENABLE_OTX", "false").lower() == "true":
            fetchers["otx"] = AlienVaultOTXFetcher(otx_key)
            logger.info("✓ AlienVault OTX fetcher enabled")
        
        # abuse.ch URLhaus (no key required)
        if os.getenv("TI_ENABLE_URLHAUS", "true").lower() == "true":
            fetchers["urlhaus"] = URLhausFetcher()
            logger.info("✓ URLhaus fetcher enabled")
        
        # abuse.ch Feodo Tracker (no key required)
        if os.getenv("TI_ENABLE_FEODO", "true").lower() == "true":
            fetchers["feodo"] = FeodoTrackerFetcher()
            logger.info("✓ Feodo Tracker fetcher enabled")
        
        # PhishTank (optional key for higher rate limits)
        if os.getenv("TI_ENABLE_PHISHTANK", "true").lower() == "true":
            phishtank_key = os.getenv("TI_PHISHTANK_API_KEY")
            fetchers["phishtank"] = PhishTankFetcher(api_key=phishtank_key)
            logger.info("✓ PhishTank fetcher enabled")
        
        if not fetchers:
            logger.warning(
                "No threat intelligence fetchers enabled. "
                "Set TI_ENABLE_* environment variables."
            )
        
        return fetchers
    
    def sync_all(self, hours: int = 24) -> dict:
        """
        Sync all enabled feeds.
        
        Args:
            hours: Look back this many hours for recent IOCs
            
        Returns:
            Dict with sync statistics
        """
        logger.info(f"Starting threat intelligence sync (last {hours} hours)")
        
        stats = {
            "total_iocs": 0,
            "by_source": {},
            "start_time": datetime.now(),
        }
        
        # Fetch from each source
        all_iocs: List[IOC] = []
        
        if "otx" in self.fetchers:
            logger.info("Fetching from AlienVault OTX...")
            iocs = self.fetchers["otx"].fetch_recent_pulses(hours=hours)
            all_iocs.extend(iocs)
            stats["by_source"]["otx"] = len(iocs)
        
        if "urlhaus" in self.fetchers:
            logger.info("Fetching from URLhaus...")
            iocs = self.fetchers["urlhaus"].fetch_recent_urls(hours=hours)
            all_iocs.extend(iocs)
            stats["by_source"]["urlhaus"] = len(iocs)
        
        if "feodo" in self.fetchers:
            logger.info("Fetching from Feodo Tracker...")
            iocs = self.fetchers["feodo"].fetch_c2_servers()
            all_iocs.extend(iocs)
            stats["by_source"]["feodo"] = len(iocs)
        
        if "phishtank" in self.fetchers:
            logger.info("Fetching from PhishTank...")
            iocs = self.fetchers["phishtank"].fetch_phishing_urls(hours=hours)
            all_iocs.extend(iocs)
            stats["by_source"]["phishtank"] = len(iocs)
        
        # Store IOCs
        if all_iocs:
            logger.info(f"Storing {len(all_iocs)} IOCs...")
            count = self.store.add_iocs(all_iocs)
            stats["total_iocs"] = count
        
        # Cleanup old IOCs
        logger.info("Cleaning up old IOCs...")
        removed = self.store.cleanup_old_iocs()
        stats["removed_old"] = removed
        
        # Get store stats
        store_stats = self.store.get_stats()
        stats["store_total"] = store_stats.get("total", 0)
        
        stats["end_time"] = datetime.now()
        stats["duration_seconds"] = (
            stats["end_time"] - stats["start_time"]
        ).total_seconds()
        
        logger.info(
            f"Sync complete: {stats['total_iocs']} IOCs added, "
            f"{stats['removed_old']} removed, "
            f"{stats['store_total']} total in store"
        )
        
        return stats
    
    def get_store_stats(self) -> dict:
        """Get current IOC store statistics."""
        return self.store.get_stats()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Orion Sentinel Threat Intelligence Sync"
    )
    
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Look back this many hours (default: 24)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show IOC store statistics only"
    )
    
    parser.add_argument(
        "--store-path",
        type=Path,
        help="Path to IOC store database (default: /data/threat_intel.db)"
    )
    
    args = parser.parse_args()
    
    try:
        sync = ThreatIntelSync(store_path=args.store_path)
        
        if args.stats:
            # Just show stats
            stats = sync.get_store_stats()
            print("\nIOC Store Statistics:")
            print(f"  Total IOCs: {stats.get('total', 0)}")
            for ioc_type, count in stats.items():
                if ioc_type not in ["total", "total_matches", "matches_24h"]:
                    print(f"    {ioc_type}: {count}")
            print(f"  Total matches: {stats.get('total_matches', 0)}")
            print(f"  Matches (24h): {stats.get('matches_24h', 0)}")
        else:
            # Run sync
            stats = sync.sync_all(hours=args.hours)
            
            print("\nSync Statistics:")
            print(f"  Duration: {stats['duration_seconds']:.1f}s")
            print(f"  IOCs added/updated: {stats['total_iocs']}")
            print(f"  Old IOCs removed: {stats['removed_old']}")
            print(f"  Total in store: {stats['store_total']}")
            print("\n  By Source:")
            for source, count in stats.get("by_source", {}).items():
                print(f"    {source}: {count}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

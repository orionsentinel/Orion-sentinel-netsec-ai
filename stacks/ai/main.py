#!/usr/bin/env python3
"""
Orion Sentinel AI Service - Main Entry Point

Runs AI-powered threat detection pipelines in batch mode or as HTTP API.
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orion_ai.config import get_config
from orion_ai.pipelines import DeviceAnomalyPipeline, DomainRiskPipeline
from orion_ai.http_server import run_server
from orion_ai.threat_intel import ThreatIntelligenceService
from orion_ai.data_collector import DataCollector
import asyncio


def setup_logging(log_level: str):
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def run_batch_mode(interval: int):
    """
    Run detection pipelines in batch mode.
    
    Runs periodically at specified interval.
    
    Args:
        interval: Interval between runs in minutes
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting batch mode with interval: {interval} minutes")
    
    # Initialize threat intelligence (if enabled)
    config = get_config()
    threat_intel = None
    if config.threat_intel.enable_threat_intel:
        threat_intel = ThreatIntelligenceService(
            cache_path=config.threat_intel.cache_path,
            otx_api_key=config.threat_intel.otx_api_key,
            refresh_interval_hours=config.threat_intel.refresh_interval_hours
        )
        # Initial feed refresh
        logger.info("Refreshing threat intelligence feeds on startup...")
        try:
            asyncio.run(threat_intel.refresh_feeds(force=True))
        except Exception as e:
            logger.error(f"Failed to refresh threat feeds on startup: {e}")
    
    # Initialize pipelines
    device_pipeline = DeviceAnomalyPipeline()
    domain_pipeline = DomainRiskPipeline()
    
    # Main loop
    iteration = 0
    while True:
        iteration += 1
        logger.info(f"{'='*80}")
        logger.info(f"Batch iteration {iteration} started at {datetime.now()}")
        logger.info(f"{'='*80}")
        
        # Refresh threat intelligence periodically
        if threat_intel:
            try:
                asyncio.run(threat_intel.refresh_feeds())
            except Exception as e:
                logger.error(f"Failed to refresh threat feeds: {e}")
        
        try:
            # Run device anomaly detection
            logger.info("Running device anomaly detection...")
            device_results = device_pipeline.run()
            logger.info(
                f"Device anomaly detection complete: "
                f"{len(device_results)} devices processed"
            )
            
        except Exception as e:
            logger.error(f"Device anomaly detection failed: {e}", exc_info=True)
        
        try:
            # Run domain risk scoring
            logger.info("Running domain risk scoring...")
            domain_results = domain_pipeline.run()
            logger.info(
                f"Domain risk scoring complete: "
                f"{len(domain_results)} domains processed"
            )
            
        except Exception as e:
            logger.error(f"Domain risk scoring failed: {e}", exc_info=True)
        
        logger.info(f"Batch iteration {iteration} complete")
        logger.info(f"Next run in {interval} minutes")
        
        # Sleep until next iteration
        time.sleep(interval * 60)


def run_oneshot_mode(start: str, end: str, pipeline: str):
    """
    Run detection once and exit.
    
    Useful for testing or manual triggering.
    
    Args:
        start: Start time (ISO format or 'last Xh/Xm')
        end: End time (ISO format or 'now')
        pipeline: Which pipeline to run (device, domain, or both)
    """
    logger = logging.getLogger(__name__)
    
    # Parse time arguments
    if end == "now":
        end_time = datetime.now()
    else:
        end_time = datetime.fromisoformat(end)
    
    if start.startswith("last"):
        # Parse "last Xh" or "last Xm"
        parts = start.split()
        if len(parts) == 2:
            value = int(parts[1][:-1])
            unit = parts[1][-1]
            if unit == "h":
                start_time = end_time - timedelta(hours=value)
            elif unit == "m":
                start_time = end_time - timedelta(minutes=value)
            else:
                raise ValueError(f"Invalid time unit: {unit} (use h or m)")
        else:
            raise ValueError(f"Invalid start time format: {start}")
    else:
        start_time = datetime.fromisoformat(start)
    
    logger.info(f"Running one-shot detection for: {start_time} to {end_time}")
    
    # Run selected pipeline(s)
    if pipeline in ["device", "both"]:
        logger.info("Running device anomaly detection...")
        device_pipeline = DeviceAnomalyPipeline()
        device_results = device_pipeline.run(start_time=start_time, end_time=end_time)
        logger.info(f"Device anomaly detection: {len(device_results)} devices processed")
        
        # Print summary
        anomalies = [r for r in device_results if r.is_anomalous]
        if anomalies:
            logger.warning(f"Found {len(anomalies)} anomalous devices:")
            for r in anomalies:
                logger.warning(
                    f"  {r.device_ip}: score={r.anomaly_score:.3f} "
                    f"(threshold={r.threshold})"
                )
    
    if pipeline in ["domain", "both"]:
        logger.info("Running domain risk scoring...")
        domain_pipeline = DomainRiskPipeline()
        domain_results = domain_pipeline.run(start_time=start_time, end_time=end_time)
        logger.info(f"Domain risk scoring: {len(domain_results)} domains processed")
        
        # Print summary
        blocked = [r for r in domain_results if r.action == "BLOCK"]
        if blocked:
            logger.warning(f"Blocked {len(blocked)} high-risk domains:")
            for r in blocked:
                logger.warning(
                    f"  {r.domain}: score={r.risk_score:.3f}, reason={r.reason}"
                )
    
    logger.info("One-shot detection complete")


def run_collect_mode(interval: int, output_dir: str = None):
    """
    Run data collection mode for baseline training.
    
    Collects network/DNS data without running detection models.
    Use this mode for 7-30 days BEFORE training models.
    
    Args:
        interval: Collection interval in minutes
        output_dir: Directory to store collected data (default: /data/training)
    """
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info("DATA COLLECTION MODE - Building Training Baseline")
    logger.info("="*80)
    logger.info(f"Collection interval: {interval} minutes")
    logger.info(f"Output directory: {output_dir or '/data/training'}")
    logger.info("="*80)
    logger.info("")
    logger.info("IMPORTANT: Run this mode for 7-30 days to collect baseline data")
    logger.info("          before training your custom models.")
    logger.info("="*80)
    
    # Initialize data collector
    collector = DataCollector(output_dir=output_dir)
    
    # Main loop
    iteration = 0
    while True:
        iteration += 1
        logger.info(f"{'='*80}")
        logger.info(f"Collection iteration {iteration} started at {datetime.now()}")
        logger.info(f"{'='*80}")
        
        try:
            # Collect device features
            logger.info("Collecting device behavioral data...")
            device_count = collector.collect_device_data()
            logger.info(f"✓ Collected {device_count} device records")
            
        except Exception as e:
            logger.error(f"Device data collection failed: {e}", exc_info=True)
        
        try:
            # Collect domain features
            logger.info("Collecting domain features...")
            domain_count = collector.collect_domain_data()
            logger.info(f"✓ Collected {domain_count} domain records")
            
        except Exception as e:
            logger.error(f"Domain data collection failed: {e}", exc_info=True)
        
        try:
            # Collect raw logs (optional, for debugging)
            logger.info("Collecting raw logs...")
            raw_counts = collector.collect_raw_logs()
            logger.info(
                f"✓ Collected {raw_counts.get('suricata', 0)} Suricata events, "
                f"{raw_counts.get('dns', 0)} DNS events"
            )
            
        except Exception as e:
            logger.error(f"Raw log collection failed: {e}", exc_info=True)
        
        # Show collection statistics
        stats = collector.get_collection_stats()
        logger.info("")
        logger.info("Collection Statistics:")
        logger.info(f"  Device feature files: {stats['device_files']}")
        logger.info(f"  Domain feature files: {stats['domain_files']}")
        logger.info(f"  Raw log files: {stats['raw_files']}")
        logger.info(f"  Total size: {stats['total_size_mb']:.2f} MB")
        if stats.get('collection_days'):
            logger.info(f"  Collection period: {stats['collection_days']} days")
            logger.info(f"  Date range: {stats['oldest_data']} to {stats['newest_data']}")
            
            # Provide guidance on when to train
            days = stats['collection_days']
            if days < 7:
                logger.info(f"  ⚠ Collect {7 - days} more days before training (minimum 7 days)")
            elif days < 30:
                logger.info(f"  ✓ Ready for training! ({days} days collected)")
                logger.info(f"    Recommended: Collect {30 - days} more days for better baseline")
            else:
                logger.info(f"  ✓ Excellent baseline! ({days} days collected)")
                logger.info(f"    Ready to train production models")
        
        logger.info(f"{'='*80}")
        logger.info(f"Collection iteration {iteration} complete")
        logger.info(f"Next collection in {interval} minutes")
        logger.info(f"{'='*80}")
        
        # Sleep until next iteration
        time.sleep(interval * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Orion Sentinel AI Service - Network Threat Detection"
    )
    
    parser.add_argument(
        "--mode",
        choices=["batch", "api", "oneshot", "collect"],
        default="batch",
        help="Execution mode (default: batch). Use 'collect' to gather training data."
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Batch mode interval in minutes (default: from config)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="API mode port (default: 8080)"
    )
    
    parser.add_argument(
        "--start",
        type=str,
        default="last 1h",
        help="One-shot mode start time (ISO format or 'last Xh/Xm')"
    )
    
    parser.add_argument(
        "--end",
        type=str,
        default="now",
        help="One-shot mode end time (ISO format or 'now')"
    )
    
    parser.add_argument(
        "--pipeline",
        choices=["device", "domain", "both"],
        default="both",
        help="One-shot mode pipeline to run (default: both)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Log level (default: from config)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Collect mode output directory (default: /data/training)"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = get_config()
    
    # Setup logging
    log_level = args.log_level or config.log_level
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info("Orion Sentinel AI Service")
    logger.info("="*80)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Log level: {log_level}")
    logger.info("="*80)
    
    # Run in selected mode
    try:
        if args.mode == "collect":
            interval = args.interval or config.detection.batch_interval
            run_collect_mode(interval, output_dir=args.output_dir)
        
        elif args.mode == "batch":
            interval = args.interval or config.detection.batch_interval
            run_batch_mode(interval)
        
        elif args.mode == "api":
            run_server(port=args.port)
        
        elif args.mode == "oneshot":
            run_oneshot_mode(
                start=args.start,
                end=args.end,
                pipeline=args.pipeline
            )
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

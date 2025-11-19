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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Orion Sentinel AI Service - Network Threat Detection"
    )
    
    parser.add_argument(
        "--mode",
        choices=["batch", "api", "oneshot"],
        default="batch",
        help="Execution mode (default: batch)"
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
        if args.mode == "batch":
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

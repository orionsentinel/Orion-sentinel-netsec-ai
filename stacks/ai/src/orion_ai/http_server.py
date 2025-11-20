"""
HTTP API server for Orion Sentinel AI Service.

Provides REST API endpoints for triggering detections and querying results.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from orion_ai.config import get_config
from orion_ai.pipelines import DeviceAnomalyPipeline, DomainRiskPipeline

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Orion Sentinel AI API",
    description="AI-powered threat detection for network security monitoring",
    version="0.1.0"
)


# Request/response models
class DetectionRequest(BaseModel):
    """Request to trigger detection."""
    minutes_ago: Optional[int] = 10


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str


@app.get("/", response_model=dict)
async def root():
    """Root endpoint."""
    return {
        "service": "Orion Sentinel AI",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "device_anomaly": "/api/v1/detect/device",
            "domain_risk": "/api/v1/detect/domain",
            "recent_anomalies": "/api/v1/anomalies",
            "recent_domains": "/api/v1/domains"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/v1/detect/device")
async def detect_device_anomalies(minutes_ago: int = Query(default=10, ge=1, le=1440)):
    """
    Trigger device anomaly detection.
    
    Args:
        minutes_ago: Look back N minutes (default: 10)
        
    Returns:
        Detection results
    """
    logger.info(f"API: Triggering device anomaly detection (minutes_ago={minutes_ago})")
    
    try:
        pipeline = DeviceAnomalyPipeline()
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes_ago)
        
        results = pipeline.run(start_time=start_time, end_time=end_time)
        
        # Convert results to dict
        results_dict = [
            {
                "device_ip": r.device_ip,
                "anomaly_score": r.anomaly_score,
                "is_anomalous": r.is_anomalous,
                "window_start": r.window_start.isoformat(),
                "window_end": r.window_end.isoformat(),
                "threshold": r.threshold
            }
            for r in results
        ]
        
        return {
            "status": "success",
            "count": len(results),
            "anomalies_detected": sum(1 for r in results if r.is_anomalous),
            "results": results_dict
        }
        
    except Exception as e:
        logger.error(f"Device anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/detect/domain")
async def detect_domain_risks(minutes_ago: int = Query(default=60, ge=1, le=1440)):
    """
    Trigger domain risk scoring.
    
    Args:
        minutes_ago: Look back N minutes (default: 60)
        
    Returns:
        Detection results
    """
    logger.info(f"API: Triggering domain risk scoring (minutes_ago={minutes_ago})")
    
    try:
        pipeline = DomainRiskPipeline()
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes_ago)
        
        results = pipeline.run(start_time=start_time, end_time=end_time)
        
        # Convert results to dict
        results_dict = [
            {
                "domain": r.domain,
                "risk_score": r.risk_score,
                "action": r.action,
                "reason": r.reason,
                "threshold": r.threshold
            }
            for r in results
        ]
        
        return {
            "status": "success",
            "count": len(results),
            "blocked_count": sum(1 for r in results if r.action == "BLOCK"),
            "results": results_dict
        }
        
    except Exception as e:
        logger.error(f"Domain risk scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/config")
async def get_config_endpoint():
    """
    Get current configuration.
    
    Returns:
        Configuration settings (excluding secrets)
    """
    config = get_config()
    
    return {
        "detection": {
            "device_window_minutes": config.detection.device_window_minutes,
            "domain_window_minutes": config.detection.domain_window_minutes,
            "batch_interval": config.detection.batch_interval,
            "enable_blocking": config.detection.enable_blocking
        },
        "model": {
            "device_anomaly_threshold": config.model.device_anomaly_threshold,
            "domain_risk_threshold": config.model.domain_risk_threshold
        },
        "loki": {
            "url": config.loki.url
        }
    }


# TODO: Implement endpoints to query recent results from log files
# @app.get("/api/v1/anomalies")
# async def get_recent_anomalies():
#     """Get recent device anomalies."""
#     pass

# @app.get("/api/v1/domains")
# async def get_recent_domains():
#     """Get recent high-risk domains."""
#     pass


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """
    Run the HTTP API server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn
    
    logger.info(f"Starting HTTP API server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()

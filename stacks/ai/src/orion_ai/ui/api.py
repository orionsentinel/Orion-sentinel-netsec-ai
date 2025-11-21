"""
FastAPI application for Orion Sentinel Web UI.

Provides both HTML pages and JSON API endpoints.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from orion_ai.core.config import get_config
from orion_ai.ui import views

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Orion Sentinel Security Dashboard",
    description="Network Security Monitoring & AI-Powered Threat Detection",
    version="1.0.0"
)

# Setup templates
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# Setup static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ============================================================================
# HTML Pages
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Main dashboard page.
    
    Shows health score, recent events, and device summary.
    """
    try:
        data = views.get_dashboard_view()
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, **data}
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/devices", response_class=HTMLResponse)
async def devices_page(
    request: Request,
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search term")
):
    """
    Device inventory page.
    
    Lists all discovered devices with filtering and search.
    """
    try:
        device_views = views.list_devices_view(tag_filter=tag, search=search)
        return templates.TemplateResponse(
            "devices.html",
            {
                "request": request,
                "devices": device_views,
                "tag_filter": tag,
                "search_term": search,
            }
        )
    except Exception as e:
        logger.error(f"Devices page error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/device/{device_id}", response_class=HTMLResponse)
async def device_profile(request: Request, device_id: str):
    """
    Device profile page.
    
    Shows detailed information about a specific device.
    """
    try:
        profile = views.get_device_profile(device_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return templates.TemplateResponse(
            "device_profile.html",
            {"request": request, **profile}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device profile error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events", response_class=HTMLResponse)
async def events_page(
    request: Request,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    type: Optional[str] = Query(None, description="Filter by event type"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours")
):
    """
    Security events page.
    
    Shows recent security events with filtering.
    """
    try:
        severity_filter = [severity] if severity else None
        type_filter = [type] if type else None
        
        events = views.get_recent_events(
            limit=100,
            hours=hours,
            severity_filter=severity_filter,
            type_filter=type_filter
        )
        
        return templates.TemplateResponse(
            "events.html",
            {
                "request": request,
                "events": events,
                "severity_filter": severity,
                "type_filter": type,
                "hours": hours,
            }
        )
    except Exception as e:
        logger.error(f"Events page error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playbooks", response_class=HTMLResponse)
async def playbooks_page(request: Request):
    """
    SOAR playbooks management page.
    
    Shows all playbooks with their status and allows toggling them.
    """
    try:
        playbooks_data = views.get_playbooks_view()
        return templates.TemplateResponse(
            "playbooks.html",
            {
                "request": request,
                **playbooks_data
            }
        )
    except Exception as e:
        logger.error(f"Playbooks page error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """
    Settings page (placeholder).
    
    Future: Allow toggling features, updating thresholds, etc.
    """
    return templates.TemplateResponse(
        "settings.html",
        {"request": request}
    )


# ============================================================================
# JSON API Endpoints
# ============================================================================

@app.get("/api/health")
async def api_health():
    """
    Get current security health score and metrics.
    
    Returns:
        Health score data
    """
    try:
        data = views.get_dashboard_view()
        health = data.get("health_score")
        
        if health:
            return health.to_dict()
        else:
            return {"score": 0, "status": "Unknown", "metrics": {}}
    except Exception as e:
        logger.error(f"API health error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events")
async def api_events(
    limit: int = Query(50, ge=1, le=500),
    hours: int = Query(24, ge=1, le=168),
    severity: Optional[str] = None,
    type: Optional[str] = None
):
    """
    Get recent security events.
    
    Args:
        limit: Maximum number of events
        hours: Time window in hours
        severity: Optional severity filter
        type: Optional event type filter
        
    Returns:
        List of events
    """
    try:
        severity_filter = [severity] if severity else None
        type_filter = [type] if type else None
        
        events = views.get_recent_events(
            limit=limit,
            hours=hours,
            severity_filter=severity_filter,
            type_filter=type_filter
        )
        
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"API events error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices")
async def api_devices(
    tag: Optional[str] = None,
    search: Optional[str] = None
):
    """
    Get device inventory.
    
    Args:
        tag: Optional tag filter
        search: Optional search term
        
    Returns:
        List of devices
    """
    try:
        device_views = views.list_devices_view(tag_filter=tag, search=search)
        
        # Convert to JSON-serializable format
        devices_json = []
        for dv in device_views:
            device = dv["device"]
            devices_json.append({
                "device_id": device.device_id,
                "ip": device.ip,
                "mac": device.mac,
                "hostname": device.hostname,
                "first_seen": device.first_seen.isoformat(),
                "last_seen": device.last_seen.isoformat(),
                "tags": device.tags,
                "guess_type": device.guess_type,
                "owner": device.owner,
                "alert_count": dv["alert_count"],
                "anomaly_count": dv["anomaly_count"],
                "risk_level": dv["risk_level"],
            })
        
        return {"devices": devices_json, "count": len(devices_json)}
    except Exception as e:
        logger.error(f"API devices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/device/{device_id}")
async def api_device(device_id: str):
    """
    Get detailed device profile.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Device profile data
    """
    try:
        profile = views.get_device_profile(device_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Device not found")
        
        device = profile["device"]
        return {
            "device": {
                "device_id": device.device_id,
                "ip": device.ip,
                "mac": device.mac,
                "hostname": device.hostname,
                "first_seen": device.first_seen.isoformat(),
                "last_seen": device.last_seen.isoformat(),
                "tags": device.tags,
                "guess_type": device.guess_type,
                "owner": device.owner,
            },
            "events": profile["events"],
            "event_counts": profile["event_counts"],
            "timeline": profile["timeline"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API device error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def api_config():
    """
    Get current configuration (non-sensitive parts).
    
    Returns:
        Configuration data
    """
    try:
        config = get_config()
        return {
            "detection": {
                "device_window_minutes": config.detection.device_window_minutes,
                "domain_window_minutes": config.detection.domain_window_minutes,
                "enable_blocking": config.detection.enable_blocking,
            },
            "model": {
                "device_anomaly_threshold": config.model.device_anomaly_threshold,
                "domain_risk_threshold": config.model.domain_risk_threshold,
            },
            "threat_intel": {
                "enabled": config.threat_intel.enable_threat_intel,
                "refresh_interval_hours": config.threat_intel.refresh_interval_hours,
            },
        }
    except Exception as e:
        logger.error(f"API config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/playbooks")
async def api_playbooks():
    """
    Get list of all playbooks.
    
    Returns:
        List of playbooks with their configuration
    """
    try:
        playbooks_data = views.get_playbooks_view()
        playbooks = playbooks_data.get("playbooks", [])
        
        # Convert to JSON-serializable format
        playbooks_json = []
        for pb in playbooks:
            playbooks_json.append(pb.to_dict())
        
        return {
            "playbooks": playbooks_json,
            "count": len(playbooks),
            "enabled_count": playbooks_data.get("enabled_count", 0),
            "disabled_count": playbooks_data.get("disabled_count", 0),
            "dry_run_count": playbooks_data.get("dry_run_count", 0),
        }
    except Exception as e:
        logger.error(f"API playbooks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/playbooks/{playbook_id}")
async def api_playbook(playbook_id: str):
    """
    Get details of a specific playbook.
    
    Args:
        playbook_id: Playbook identifier
        
    Returns:
        Playbook details
    """
    try:
        playbook = views.get_playbook(playbook_id)
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        
        return playbook.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API playbook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/playbooks/{playbook_id}/toggle")
async def api_toggle_playbook(playbook_id: str, request: Request):
    """
    Toggle a playbook enabled/disabled.
    
    Args:
        playbook_id: Playbook identifier
        request: Request with JSON body {"enabled": true/false}
        
    Returns:
        Updated playbook data
    """
    try:
        body = await request.json()
        enabled = body.get("enabled", True)
        
        success = views.toggle_playbook(playbook_id, enabled)
        if not success:
            raise HTTPException(status_code=404, detail="Playbook not found")
        
        # Get updated playbook
        playbook = views.get_playbook(playbook_id)
        return {
            "success": True,
            "playbook": playbook.to_dict() if playbook else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API toggle playbook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Server Startup
# ============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8080):
    """
    Run the web UI server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn
    
    logger.info(f"Starting Orion Sentinel Web UI on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()

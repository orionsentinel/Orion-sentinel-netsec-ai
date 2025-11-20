"""
Orion Sentinel Wizard - FastAPI Application

First-run web wizard for configuring the Security Pi.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .views import WizardConfig, apply_configuration, check_setup_done, mark_setup_done, test_pihole_connection

# Setup paths
WIZARD_DIR = Path(__file__).parent
TEMPLATES_DIR = WIZARD_DIR / "templates"
STATIC_DIR = WIZARD_DIR / "static"
CONFIG_CACHE_FILE = Path("/tmp/wizard_config.json")

# Create FastAPI app
app = FastAPI(
    title="Orion Sentinel Setup Wizard",
    description="First-run configuration wizard for Orion Sentinel Security Pi",
    version="0.1.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def save_temp_config(config: WizardConfig) -> None:
    """Save configuration to temporary file."""
    CONFIG_CACHE_FILE.write_text(config.model_dump_json())


def load_temp_config() -> Optional[WizardConfig]:
    """Load configuration from temporary file."""
    if CONFIG_CACHE_FILE.exists():
        try:
            data = json.loads(CONFIG_CACHE_FILE.read_text())
            return WizardConfig(**data)
        except Exception:
            return None
    return None


def clear_temp_config() -> None:
    """Clear temporary configuration file."""
    if CONFIG_CACHE_FILE.exists():
        CONFIG_CACHE_FILE.unlink()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Main entry point - redirect based on setup status.
    """
    if check_setup_done():
        return templates.TemplateResponse(
            "setup_complete.html",
            {"request": request}
        )
    else:
        return RedirectResponse(url="/wizard/welcome")


@app.get("/wizard/welcome", response_class=HTMLResponse)
async def wizard_welcome(request: Request):
    """
    Step 1: Welcome page.
    """
    if check_setup_done():
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse(
        "wizard_welcome.html",
        {"request": request}
    )


@app.get("/wizard/dns", response_class=HTMLResponse)
async def wizard_dns_get(request: Request, error: Optional[str] = None):
    """
    Step 2: DNS Pi connection configuration.
    """
    if check_setup_done():
        return RedirectResponse(url="/")
    
    # Load existing config if available
    config = load_temp_config()
    
    return templates.TemplateResponse(
        "wizard_dns.html",
        {
            "request": request,
            "error": error,
            "dns_pi_ip": config.dns_pi_ip if config else None,
            "pihole_enabled": config.pihole_enabled if config else False,
            "pihole_api_token": config.pihole_api_token if config else None
        }
    )


@app.post("/wizard/dns")
async def wizard_dns_post(
    request: Request,
    dns_pi_ip: str = Form(...),
    pihole_enabled: bool = Form(False),
    pihole_api_token: str = Form("")
):
    """
    Process DNS Pi configuration.
    """
    # Create or update config
    config = load_temp_config() or WizardConfig()
    config.dns_pi_ip = dns_pi_ip
    config.pihole_enabled = pihole_enabled
    config.pihole_api_token = pihole_api_token if pihole_enabled else None
    
    # Test connection if Pi-hole is enabled
    if pihole_enabled and pihole_api_token:
        success, message = test_pihole_connection(dns_pi_ip, pihole_api_token)
        if not success:
            return templates.TemplateResponse(
                "wizard_dns.html",
                {
                    "request": request,
                    "error": f"Pi-hole connection failed: {message}",
                    "dns_pi_ip": dns_pi_ip,
                    "pihole_enabled": pihole_enabled,
                    "pihole_api_token": pihole_api_token
                }
            )
    
    # Save and proceed
    save_temp_config(config)
    return RedirectResponse(url="/wizard/mode", status_code=303)


@app.get("/wizard/mode", response_class=HTMLResponse)
async def wizard_mode_get(request: Request):
    """
    Step 3: Network and operating mode configuration.
    """
    if check_setup_done():
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse(
        "wizard_mode.html",
        {"request": request}
    )


@app.post("/wizard/mode")
async def wizard_mode_post(
    request: Request,
    nsm_iface: str = Form("eth0"),
    operating_mode: str = Form("observe")
):
    """
    Process network and mode configuration.
    """
    # Load and update config
    config = load_temp_config() or WizardConfig()
    config.nsm_iface = nsm_iface
    config.operating_mode = operating_mode
    
    # Save and proceed
    save_temp_config(config)
    return RedirectResponse(url="/wizard/features", status_code=303)


@app.get("/wizard/features", response_class=HTMLResponse)
async def wizard_features_get(request: Request):
    """
    Step 4: AI and intel features configuration.
    """
    if check_setup_done():
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse(
        "wizard_features.html",
        {"request": request}
    )


@app.post("/wizard/features")
async def wizard_features_post(
    request: Request,
    enable_ai: bool = Form(False),
    enable_intel: bool = Form(False)
):
    """
    Process features configuration.
    """
    # Load and update config
    config = load_temp_config() or WizardConfig()
    config.enable_ai = enable_ai
    config.enable_intel = enable_intel
    
    # Save and proceed
    save_temp_config(config)
    return RedirectResponse(url="/wizard/finish", status_code=303)


@app.get("/wizard/finish", response_class=HTMLResponse)
async def wizard_finish_get(request: Request):
    """
    Step 5: Apply configuration and finish.
    """
    if check_setup_done():
        return RedirectResponse(url="/")
    
    # Load config
    config = load_temp_config()
    if not config:
        # No config, redirect to start
        return RedirectResponse(url="/wizard/welcome")
    
    # Apply configuration
    success, message = apply_configuration(config)
    
    # Mark setup as done and clear temp config
    if success:
        mark_setup_done()
        clear_temp_config()
    
    return templates.TemplateResponse(
        "wizard_finish.html",
        {
            "request": request,
            "success": success,
            "message": message,
            "config": config
        }
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "ok", "setup_complete": check_setup_done()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)

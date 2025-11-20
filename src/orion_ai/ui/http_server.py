"""
Main HTTP server for Orion Sentinel UI APIs.

Serves device profile and assistant endpoints.
"""

import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .assistant_api import router as assistant_router
from .device_profile_api import router as device_router

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Orion Sentinel API",
    description="Security monitoring and device management API",
    version="0.2.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(device_router)
app.include_router(assistant_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Orion Sentinel API",
        "version": "0.2.0",
        "endpoints": {
            "devices": "/device",
            "assistant": "/assistant",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


def main():
    """Main entry point for HTTP server."""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info("=" * 60)
    logger.info("Orion Sentinel - API Server")
    logger.info("=" * 60)
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info("=" * 60)
    logger.info(f"API Documentation: http://{host}:{port}/docs")
    logger.info("=" * 60)
    
    uvicorn.run(
        "orion_ai.ui.http_server:app",
        host=host,
        port=port,
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )


if __name__ == "__main__":
    main()

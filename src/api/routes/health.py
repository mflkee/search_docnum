from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime

# Internal imports
from src.utils.logging_config import app_logger

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Check the health status of the service.
    """
    try:
        # In a real application, you might check database connections,
        # external API availability, etc.
        # For now, just return a simple healthy status
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "Arshin Registry Synchronization System",
            "version": "1.0.0"
        }
        
        app_logger.info("Health check endpoint accessed")
        return health_status
        
    except Exception as e:
        app_logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
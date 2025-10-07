import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.middleware.error_handler import ErrorHandlingMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.config.settings import settings
from src.utils.logging_config import app_logger

# Create upload and results directories if they don't exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.results_dir, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API for synchronizing measurement instruments registry data with the state Arshin registry"
)

# Add rate limiting middleware (apply to all requests)
app.add_middleware(
    RateLimitMiddleware,
    requests_limit=100,  # 100 requests per minute per IP
    window_size=60
)

# Add error handling middleware
app.add_middleware(
    ErrorHandlingMiddleware
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="src/templates")

# Import and include routes after app creation to avoid circular imports
from src.api.routes import health, results, status, upload, web_interface

# Include API routes
app.include_router(upload.router, prefix=settings.api_v1_prefix, tags=["upload"])
app.include_router(status.router, prefix=settings.api_v1_prefix, tags=["status"])
app.include_router(results.router, prefix=settings.api_v1_prefix, tags=["results"])
app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["health"])

# Include web interface routes
app.include_router(web_interface.router, tags=["web_interface"])

@app.on_event("startup")
async def startup_event():
    app_logger.info("Starting up Arshin Registry Synchronization System")


@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("Shutting down Arshin Registry Synchronization System")


@app.get("/")
async def root():
    """
    Main page with file upload interface
    """
    return {"message": "Welcome to Arshin Registry Synchronization System"}

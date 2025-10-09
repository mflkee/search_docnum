"""Runtime entry point for starting the FastAPI application via uvicorn."""

from __future__ import annotations

import os
from typing import Any

import uvicorn


def _env_flag(name: str, default: bool = False) -> bool:
    """Return True when the named environment variable represents an enabled flag."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def main() -> None:
    """Start uvicorn with settings derived from environment variables."""
    app_path = os.getenv("APP_MODULE", "src.api.main:app")
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    log_level = os.getenv("APP_LOG_LEVEL", "info")
    reload_enabled = _env_flag("APP_RELOAD", False)
    proxy_headers = _env_flag("APP_PROXY_HEADERS", True)
    forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")

    worker_kwargs: dict[str, Any] = {}
    workers_env = os.getenv("APP_WORKERS")
    if workers_env:
        workers = max(1, int(workers_env))
        worker_kwargs["workers"] = workers
        if workers > 1 and reload_enabled:
            # uvicorn does not support reloading with multiple workers
            reload_enabled = False

    uvicorn.run(
        app_path,
        host=host,
        port=port,
        log_level=log_level,
        reload=reload_enabled,
        proxy_headers=proxy_headers,
        forwarded_allow_ips=forwarded_allow_ips,
        **worker_kwargs,
    )

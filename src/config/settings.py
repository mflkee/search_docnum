from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Arshin Registry Synchronization System"
    version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"

    # File upload settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB in bytes
    allowed_file_types: list = [".xlsx", ".xls"]

    # Arshin API settings
    arshin_api_base_url: str = "https://fgis.gost.ru/fundmetrology/eapi"

    # Task processing settings
    task_poll_interval: int = 5  # seconds
    task_timeout: int = 300  # 5 minutes in seconds

    # Rate limiting for Arshin API
    arshin_api_rate_limit: int = 0  # requests per period (0 disables throttling)
    arshin_api_rate_period: int = 1  # seconds
    arshin_api_rate_penalty_limit: int = 0  # fallback window size after 429/timeout (0 disables penalty)
    arshin_api_rate_penalty_duration: int = 30  # seconds to keep penalty in effect
    arshin_api_timeout_seconds: float = 45.0  # HTTP timeout for Arshin requests
    arshin_max_concurrent_requests: int = 24  # simultaneous API requests (governed by throttler)
    arshin_stage2_batch_size: int = 2  # Stage 2 attempts executed concurrently per batch

    # Celery settings (if used)
    celery_broker_url: str = "redis://localhost:6379"
    celery_result_backend: str = "redis://localhost:6379"

    # File storage
    upload_dir: str = "uploads"
    results_dir: str = "results"

    class Config:
        env_file = ".env"


settings = Settings()

from celery import Celery
from src.config.settings import settings


# Initialize Celery app
celery_app = Celery(
    "arshin_sync",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.services.excel_parser",
        "src.services.arshin_client", 
        "src.services.data_processor",
        "src.services.report_generator"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,  # Results expire after 1 hour
    task_routes={
        "process_excel_file": {"queue": "excel_processing"},
        "fetch_arshin_data": {"queue": "api_requests"},
    },
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    task_acks_late=True,  # Acknowledge tasks after they're completed
)


if __name__ == "__main__":
    celery_app.start()
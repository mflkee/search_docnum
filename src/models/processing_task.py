from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class ProcessingTaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingTask(BaseModel):
    """
    Represents an asynchronous processing job with status tracking.
    """
    task_id: str
    status: ProcessingTaskStatus
    progress: int = 0  # Progress percentage (0-100)
    created_at: datetime
    completed_at: Optional[datetime] = None
    file_path: str
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    summary: Optional[dict[str, int]] = None
    preview_path: Optional[str] = None
    total_records: Optional[int] = None
    processed_records: int = 0

    @field_validator('progress')
    @classmethod
    def validate_progress(cls, v):
        """
        Validate that progress is between 0 and 100
        """
        if v < 0 or v > 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

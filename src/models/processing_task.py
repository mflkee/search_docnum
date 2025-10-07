from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


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
    
    def __init__(self, **data):
        super().__init__(**data)
        # Validate progress is between 0 and 100
        if self.progress < 0 or self.progress > 100:
            raise ValueError("Progress must be between 0 and 100")
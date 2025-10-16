from typing import Any

from fastapi import APIRouter, HTTPException

from src.api.routes.upload import active_tasks  # Using the same global task store

# Internal imports
from src.models.processing_task import ProcessingTaskStatus
from src.utils.logging_config import app_logger

router = APIRouter()

@router.get("/status/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """
    Check the processing status of a task.
    """
    try:
        # Check if task exists in active tasks
        if task_id not in active_tasks:
            app_logger.warning(f"Status requested for unknown task {task_id}")
            return {
                "task_id": task_id,
                "status": "NOT_FOUND",
                "progress": 0,
                "result_available": False,
                "created_at": None,
                "completed_at": None,
                "error_message": "Task ID not found"
            }

        task = active_tasks[task_id]

        # Prepare response
        response = {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "result_available": task.status == ProcessingTaskStatus.COMPLETED and task.result_path is not None,
            "dataset_available": task.status == ProcessingTaskStatus.COMPLETED and task.preview_path is not None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "summary": task.summary or {},
            "processed_records": task.processed_records,
            "total_records": task.total_records,
            "processing_time_seconds": task.processing_time_seconds,
        }

        # Include error message if task failed
        if task.status == ProcessingTaskStatus.FAILED and task.error_message:
            response["error_message"] = task.error_message

        app_logger.info(f"Status requested for task {task_id}, status: {task.status.value}, progress: {task.progress}%")

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        app_logger.error(f"Error getting status for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {e!s}")

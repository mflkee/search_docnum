import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from src.api.routes.upload import active_tasks  # Using the same global task store

# Internal imports
from src.models.processing_task import ProcessingTaskStatus
from src.utils.logging_config import app_logger

router = APIRouter()

@router.get("/results/{task_id}")
async def get_results(task_id: str):
    """
    Download the processed results if available.
    """
    try:
        # Check if task exists in active tasks
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Task ID not found")

        task = active_tasks[task_id]

        # Check if task is completed and has results
        if task.status != ProcessingTaskStatus.COMPLETED:
            if task.status == ProcessingTaskStatus.FAILED:
                raise HTTPException(status_code=409, detail=f"Task failed: {task.error_message or 'Unknown error'}")
            else:
                raise HTTPException(status_code=409, detail="Task not completed or failed")

        if not task.result_path or not os.path.exists(task.result_path):
            raise HTTPException(status_code=500, detail="Result file not found")

        app_logger.info(f"Results downloaded for task {task_id}")

        # Return the result file as a download
        return FileResponse(
            path=task.result_path,
            filename=f"arshin_results_{task_id}.xlsx",
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        app_logger.error(f"Error getting results for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Results retrieval failed: {e!s}")


@router.get("/results/{task_id}/dataset")
async def get_results_dataset(task_id: str):
    """Return processed dataset as JSON for interactive preview."""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Task ID not found")

        task = active_tasks[task_id]

        if task.status != ProcessingTaskStatus.COMPLETED:
            raise HTTPException(status_code=409, detail="Task is not completed")

        if not task.preview_path or not os.path.exists(task.preview_path):
            raise HTTPException(status_code=404, detail="Dataset preview not available")

        with open(task.preview_path, 'r', encoding='utf-8') as dataset_file:
            payload = json.load(dataset_file)

        return JSONResponse(payload)

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Error getting dataset for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Dataset retrieval failed: {e!s}")

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

# Internal imports
from src.api.routes.upload import active_tasks  # Using the same global task store
from src.models.processing_task import ProcessingTaskStatus
from src.services.progress_notifier import ProgressNotifier
from src.utils.web_utils import log_user_action

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")

@router.get("/", response_class=HTMLResponse)
async def get_upload_page(request: Request):
    """
    Main page with file upload interface.
    """
    log_user_action("web_interface_accessed", details={"page": "upload"})
    return templates.TemplateResponse("upload.html", {"request": request})

@router.get("/status/{task_id}", response_class=HTMLResponse)
async def get_status_page(request: Request, task_id: str):
    """Legacy status endpoint redirecting to the unified results page."""
    if task_id not in active_tasks:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "task_id": task_id,
                "error": "Task ID not found",
                "dataset_available": False,
                "summary": {},
                "download_url": "",
                "dataset_url": "",
                "default_dataset_url": f"/api/v1/results/{task_id}/dataset",
                "default_download_url": f"/api/v1/results/{task_id}",
                "status_url": f"/api/task-status/{task_id}",
                "stream_url": "",
                "status_value": "NOT_FOUND",
                "progress": 0,
                "completed": False,
                "created_at": None,
                "completed_at": None,
                "processed_records": 0,
                "total_records": 0
            }
        )

    log_user_action("status_page_redirect", details={"task_id": task_id})
    return RedirectResponse(f"/results/{task_id}", status_code=303)

@router.get("/results/{task_id}", response_class=HTMLResponse)
async def get_results_page(request: Request, task_id: str):
    """
    Page with download link for processed results.
    """
    task = active_tasks.get(task_id)

    if not task:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "task_id": task_id,
                "error": "Task ID not found",
                "dataset_available": False,
                "summary": {},
                "download_url": "",
                "dataset_url": "",
                "default_dataset_url": f"/api/v1/results/{task_id}/dataset",
                "default_download_url": f"/api/v1/results/{task_id}",
                "status_url": f"/api/task-status/{task_id}",
                "stream_url": "",
                "status_value": "NOT_FOUND",
                "progress": 0,
                "completed": False,
                "created_at": None,
                "completed_at": None,
                "processed_records": 0,
                "total_records": 0
            }
        )

    dataset_available = bool(task.preview_path and os.path.exists(task.preview_path))
    download_available = bool(task.result_path and os.path.exists(task.result_path))

    log_user_action("results_page_viewed", details={"task_id": task_id})

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "task_id": task_id,
            "error": task.error_message if task.status == ProcessingTaskStatus.FAILED else None,
            "dataset_available": dataset_available,
            "summary": task.summary or {},
            "download_url": f"/api/v1/results/{task_id}" if download_available else "",
            "dataset_url": f"/api/v1/results/{task_id}/dataset" if dataset_available else "",
            "default_dataset_url": f"/api/v1/results/{task_id}/dataset",
            "default_download_url": f"/api/v1/results/{task_id}",
            "status_url": f"/api/task-status/{task_id}",
            "stream_url": f"/api/task-stream/{task_id}",
            "status_value": task.status.value,
            "progress": task.progress,
            "completed": task.status == ProcessingTaskStatus.COMPLETED,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "processed_records": task.processed_records,
        "total_records": task.total_records or 0,
        "processing_time_seconds": task.processing_time_seconds,
        }
    )

@router.get("/api/task-status/{task_id}")
async def get_task_status_for_web(task_id: str):
    """
    API endpoint to get task status for AJAX requests from web interface.
    """
    if task_id not in active_tasks:
        return {"error": "Task not found"}

    task = active_tasks[task_id]

    dataset_available = bool(task.preview_path and os.path.exists(task.preview_path))
    result_available = bool(task.result_path and os.path.exists(task.result_path))

    payload = {
        "status": task.status.value,
        "progress": task.progress,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message if task.status == ProcessingTaskStatus.FAILED else None,
        "dataset_available": dataset_available,
        "result_available": result_available,
        "summary": task.summary or {},
        "processed_records": task.processed_records if task.processed_records is not None else 0,
        "total_records": task.total_records if task.total_records is not None else 0,
        "processing_time_seconds": task.processing_time_seconds,
    }

    return payload


@router.get("/api/task-stream/{task_id}")
async def stream_task_progress(task_id: str):
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]
    dataset_available = bool(task.preview_path and os.path.exists(task.preview_path))
    result_available = bool(task.result_path and os.path.exists(task.result_path))

    initial_payload = {
        "type": "snapshot",
        "task_id": task.task_id,
        "status": task.status.value,
        "progress": task.progress,
        "processed": task.processed_records or 0,
        "total": task.total_records or 0,
        "summary": task.summary or {},
        "dataset_available": dataset_available,
        "result_available": result_available,
        "log_messages": task.log_messages[-50:] if task.log_messages else [],
        "last_log_message": task.last_log_message,
    }

    stream = ProgressNotifier.stream(task_id, initial_payload)
    headers = {
        "Cache-Control": "no-store",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(stream, media_type="text/event-stream", headers=headers)

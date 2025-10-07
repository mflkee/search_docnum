from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Internal imports
from src.api.routes.upload import active_tasks  # Using the same global task store
from src.models.processing_task import ProcessingTaskStatus
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
    """
    Page showing processing status with progress updates.
    """
    # Check if task exists
    if task_id not in active_tasks:
        # Instead of raising an HTTP error, render an error page
        return templates.TemplateResponse(
            "status.html",
            {
                "request": request,
                "task_id": task_id,
                "error": "Task ID not found",
                "task": None
            }
        )

    task = active_tasks[task_id]
    log_user_action("status_page_viewed", details={"task_id": task_id})

    return templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "task_id": task_id,
            "task": task,
            "error": None
        }
    )

@router.get("/results/{task_id}", response_class=HTMLResponse)
async def get_results_page(request: Request, task_id: str):
    """
    Page with download link for processed results.
    """
    # Check if task exists
    if task_id not in active_tasks:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "task_id": task_id,
                "error": "Task ID not found",
                "can_download": False
            }
        )

    task = active_tasks[task_id]

    # Check if task is completed and has results
    if task.status != ProcessingTaskStatus.COMPLETED:
        if task.status == ProcessingTaskStatus.FAILED:
            error_msg = f"Task failed: {task.error_message or 'Unknown error'}"
        else:
            error_msg = f"Task not completed (current status: {task.status.value})"

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "task_id": task_id,
                "error": error_msg,
                "can_download": False
            }
        )

    if not task.result_path:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "task_id": task_id,
                "error": "Result file not available",
                "can_download": False
            }
        )

    log_user_action("results_page_viewed", details={"task_id": task_id})

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "task_id": task_id,
            "error": None,
            "can_download": True,
            "result_path": task.result_path
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

    return {
        "status": task.status.value,
        "progress": task.progress,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message
    }

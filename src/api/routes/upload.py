import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from src.config.settings import settings

# Internal imports
from src.models.processing_task import ProcessingTask, ProcessingTaskStatus
from src.services.data_processor import DataProcessorService
from src.services.file_validator import FileValidator
from src.services.report_generator import ReportGeneratorService
from src.utils.logging_config import app_logger
from src.utils.web_utils import create_file_path, log_user_action, sanitize_filename

router = APIRouter()

# Global task store (in production, use Redis or database)
active_tasks = {}

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    verification_date_column: Optional[str] = Form(default="Дата поверки"),
    certificate_number_column: Optional[str] = Form(default="Наличие документа с отметкой о поверке (№ св-ва о поверке)"),
    sheet_name: Optional[str] = Form(default="Перечень")
):
    """
    Upload an Excel file for processing and initiate background task.

    Args:
        file: The Excel file to upload
        verification_date_column: Column header or Excel reference for verification date (default 'Дата поверки')
        certificate_number_column: Column header or Excel reference for certificate number (default 'Наличие документа с отметкой о поверке (№ св-ва о поверке)')
        sheet_name: Name of the sheet to parse (default 'Перечень')
    """
    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    try:
        # Validate file type and security
        # First save the file temporarily to validate it
        safe_filename = sanitize_filename(file.filename)
        temp_file_path = create_file_path('upload', f"{task_id}_{safe_filename}")

        # Save the uploaded file temporarily
        try:
            content = await file.read()
            file_size = len(content)

            # Check file size before saving
            if file_size > settings.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size {file_size} exceeds maximum allowed size {settings.max_file_size}"
                )

            with open(temp_file_path, 'wb') as buffer:
                buffer.write(content)
        except Exception as e:
            app_logger.error(f"Error saving uploaded file: {e}")
            raise HTTPException(status_code=500, detail="Error saving uploaded file")

        # Validate the file
        is_valid, error_msg = FileValidator.validate_file_type(temp_file_path)
        if not is_valid:
            os.remove(temp_file_path)  # Clean up invalid file
            raise HTTPException(status_code=422, detail=error_msg)

        # Create initial processing task
        processing_task = ProcessingTask(
            task_id=task_id,
            status=ProcessingTaskStatus.PENDING,
            progress=0,
            created_at=datetime.now(timezone.utc),
            file_path=temp_file_path,
            result_path=None,
            error_message=None
        )

        # Store the task in the global task store
        active_tasks[task_id] = processing_task

        # Log the upload action
        log_user_action("file_upload_started", details={
            "task_id": task_id,
            "filename": file.filename,
            "file_size": file_size,
            "verification_date_column": verification_date_column,
            "certificate_number_column": certificate_number_column,
            "sheet_name": sheet_name
        })

        # Add background task for processing with column identifiers
        background_tasks.add_task(
            process_file_background,
            task_id,
            temp_file_path,
            verification_date_column,
            certificate_number_column,
            sheet_name
        )

        # Return task ID and status in a format suitable for external systems
        return {
            "task_id": task_id,
            "status": processing_task.status.value,
            "message": "File uploaded and processing started",
            "file_info": {
                "name": file.filename,
                "size": file_size,
                "type": file.content_type
            },
            "columns_used": {
                "verification_date": verification_date_column,
                "certificate_number": certificate_number_column
            },
            "sheet_used": {
                "sheet_name": sheet_name
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        app_logger.error(f"Error in upload endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {e!s}")


async def process_file_background(
    task_id: str,
    file_path: str,
    verification_date_column: str = "Дата поверки",
    certificate_number_column: str = "Наличие документа с отметкой о поверке (№ св-ва о поверке)",
    sheet_name: str = "Перечень"
):
    """
    Process the uploaded file in the background

    Args:
        task_id: The ID of the processing task
        file_path: Path to the uploaded file
        verification_date_column: Column header or Excel reference for verification date
        certificate_number_column: Column header or Excel reference for certificate number
        sheet_name: Name of the sheet to parse (default 'Перечень')
    """
    data_processor: Optional[DataProcessorService] = None
    try:
        # Get the task from the store
        if task_id not in active_tasks:
            app_logger.error(f"Task {task_id} not found in active tasks")
            return

        task = active_tasks[task_id]
        task.status = ProcessingTaskStatus.PROCESSING
        task.progress = 5  # Start at 5% to show processing began

        app_logger.info(f"Starting background processing for task {task_id}")

        # Initialize services
        data_processor = DataProcessorService()
        report_generator = ReportGeneratorService()

        # Process the Excel file with progress tracking and column identifiers
        reports = await data_processor.process_with_progress_tracking(
            file_path,
            task_id,
            verification_date_column,
            certificate_number_column,
            sheet_name
        )

        statistics = data_processor._compute_processing_statistics(reports)
        task.summary = {
            "processed": statistics.get("processed", 0),
            "updated": statistics.get("updated", 0),
            "unchanged": statistics.get("unchanged", 0),
            "not_found": statistics.get("not_found", 0),
            "errors": statistics.get("errors", 0),
            "invalid_format": statistics.get("invalid_format", 0),
        }
        task.processed_records = statistics.get("processed", 0)
        if task.total_records is None:
            task.total_records = statistics.get("processed", 0)

        # Persist dataset preview for UI consumption
        dataset_payload = {
            "task_id": task_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": statistics,
            "reports": [report.model_dump() for report in reports]
        }

        dataset_file_path = create_file_path('result', f"report_{task_id}.json")
        with open(dataset_file_path, 'w', encoding='utf-8') as dataset_file:
            json.dump(dataset_payload, dataset_file, ensure_ascii=False)

        # Update task progress to 90% - nearly complete
        task.progress = 90

        # Generate the report file
        result_file_path = create_file_path('result', f"report_{task_id}.xlsx")
        report_generator.generate_report(reports, result_file_path)

        # Update task with result path
        task.result_path = result_file_path
        task.preview_path = dataset_file_path
        task.summary = statistics
        task.progress = 100
        task.status = ProcessingTaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)

        app_logger.info(f"Completed processing for task {task_id}, result at {result_file_path}")

        # Clean up the original uploaded file
        try:
            os.remove(file_path)
            app_logger.info(f"Cleaned up original file {file_path}")
        except OSError as e:
            app_logger.warning(f"Could not remove original file {file_path}: {e}")

    except Exception as e:
        app_logger.error(f"Error in background processing for task {task_id}: {e}")

        # Update task with error
        if task_id in active_tasks:
            task = active_tasks[task_id]
            task.status = ProcessingTaskStatus.FAILED
            task.error_message = str(e)
            task.progress = 100  # Mark as complete (with failure)
            task.completed_at = datetime.now(timezone.utc)
    finally:
        if data_processor is not None:
            await data_processor.close()

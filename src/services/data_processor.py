from typing import List, Dict
from src.models.excel_data import ExcelRegistryData
from src.models.arshin_record import ArshinRegistryRecord
from src.models.processing_task import ProcessingTask, ProcessingTaskStatus
from src.models.report import Report, ProcessingStatus
from src.services.excel_parser import ExcelParserService
from src.services.arshin_client import ArshinClientService
from src.utils.validators import validate_certificate_format
from src.utils.logging_config import app_logger
import uuid
import asyncio
from datetime import datetime


class DataProcessorService:
    """
    Service for processing Excel data and matching with Arshin registry.
    Handles the core logic of matching Excel records with Arshin data.
    """
    
    def __init__(self):
        self.excel_parser = ExcelParserService()
        self.arshin_client = ArshinClientService()
    
    async def process_excel_file(self, file_path: str, task_id: str = None, 
                                verification_date_column: str = "AE", 
                                certificate_number_column: str = "AI") -> List[Report]:
        """
        Process an Excel file by matching its records with Arshin registry data.
        
        Args:
            file_path: Path to the Excel file to process
            task_id: Optional task ID for tracking
            verification_date_column: Column identifier for verification date (default 'AE' or 'Дата поверки')
            certificate_number_column: Column identifier for certificate number (default 'AI' or 'Наличие документа с отметкой о поверке (№ св-ва о поверке)')
            
        Returns:
            List of Report objects containing matched data
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        app_logger.info(f"Starting processing of file {file_path} with task ID {task_id}")
        
        try:
            # Parse the Excel file to get ExcelRegistryData objects
            excel_data_list = self.excel_parser.parse_excel_file(
                file_path, 
                verification_date_column, 
                certificate_number_column
            )
            app_logger.info(f"Parsed {len(excel_data_list)} records from Excel file")
            
            if not excel_data_list:
                app_logger.warning(f"No valid records found in Excel file {file_path}")
                return []
            
            reports = []
            
            # Process each Excel record
            for idx, excel_record in enumerate(excel_data_list):
                # Update progress periodically
                if idx % 10 == 0 and len(excel_data_list) > 0:
                    progress = int((idx / len(excel_data_list)) * 50)  # First 50% for processing
                    app_logger.info(f"Processing progress: {progress}% for task {task_id}")
                
                report = await self._process_single_record(excel_record, idx + 1)
                reports.append(report)
            
            app_logger.info(f"Completed processing {len(reports)} records for task {task_id}")
            return reports
            
        except Exception as e:
            app_logger.error(f"Error processing Excel file {file_path}: {e}")
            raise
    
    async def _process_single_record(self, excel_record: ExcelRegistryData, row_number: int) -> Report:
        """
        Process a single Excel record against the Arshin registry.
        
        Args:
            excel_record: The Excel record to process
            row_number: The row number in the original Excel file
            
        Returns:
            Report object with the processing result
        """
        try:
            # Validate certificate number format
            if not validate_certificate_format(excel_record.certificate_number):
                return Report(
                    arshin_id=None,
                    org_title=None,
                    mit_number=None,
                    mit_title=None,
                    mit_notation=None,
                    mi_number=excel_record.serial_number or "",
                    verification_date=excel_record.verification_date.strftime("%Y-%m-%d"),
                    valid_date=None,
                    result_docnum=None,
                    processing_status=ProcessingStatus.INVALID_CERT_FORMAT,
                    excel_source_row=row_number
                )
            
            # Extract year from verification date
            year = excel_record.verification_date.year
            
            # Query Arshin registry using the certificate number and year
            arshin_record = await self.arshin_client.get_instrument_by_certificate(
                excel_record.certificate_number, 
                year
            )
            
            if arshin_record:
                # Successfully matched
                return Report(
                    arshin_id=arshin_record.vri_id,
                    org_title=arshin_record.org_title,
                    mit_number=arshin_record.mit_number,
                    mit_title=arshin_record.mit_title,
                    mit_notation=arshin_record.mit_notation,
                    mi_number=arshin_record.mi_number,
                    verification_date=arshin_record.verification_date.strftime("%Y-%m-%d"),
                    valid_date=arshin_record.valid_date.strftime("%Y-%m-%d") if arshin_record.valid_date else None,
                    result_docnum=arshin_record.result_docnum,
                    processing_status=ProcessingStatus.MATCHED,
                    excel_source_row=row_number
                )
            else:
                # Record not found in Arshin registry
                return Report(
                    arshin_id=None,
                    org_title=None,
                    mit_number=None,
                    mit_title=None,
                    mit_notation=None,
                    mi_number=excel_record.serial_number or "",
                    verification_date=excel_record.verification_date.strftime("%Y-%m-%d"),
                    valid_date=None,
                    result_docnum=None,
                    processing_status=ProcessingStatus.NOT_FOUND,
                    excel_source_row=row_number
                )
                
        except Exception as e:
            app_logger.error(f"Error processing record with certificate {excel_record.certificate_number}: {e}")
            # Return error status report
            return Report(
                arshin_id=None,
                org_title=None,
                mit_number=None,
                mit_title=None,
                mit_notation=None,
                mi_number=excel_record.serial_number or "",
                verification_date=excel_record.verification_date.strftime("%Y-%m-%d"),
                valid_date=None,
                result_docnum=None,
                processing_status=ProcessingStatus.ERROR,
                excel_source_row=row_number
            )
    
    async def process_records_batch(self, excel_records: List[ExcelRegistryData]) -> List[Report]:
        """
        Process a batch of Excel records against the Arshin registry.
        
        Args:
            excel_records: List of ExcelRegistryData objects to process
            
        Returns:
            List of Report objects with the processing results
        """
        reports = []
        
        for idx, excel_record in enumerate(excel_records):
            report = await self._process_single_record(excel_record, idx + 1)
            reports.append(report)
        
        return reports
    
    def create_processing_task(self, file_path: str, task_id: str = None) -> ProcessingTask:
        """
        Create a processing task object for tracking file processing.
        
        Args:
            file_path: Path to the file being processed
            task_id: Optional task ID (will be generated if not provided)
            
        Returns:
            ProcessingTask object
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        return ProcessingTask(
            task_id=task_id,
            status=ProcessingTaskStatus.PENDING,
            progress=0,
            created_at=datetime.now(),
            file_path=file_path
        )
    
    async def update_task_progress(self, task: ProcessingTask, progress: int, status: ProcessingTaskStatus = None):
        """
        Update the progress and status of a processing task.
        
        Args:
            task: The ProcessingTask object to update
            progress: Progress percentage (0-100)
            status: Optional new status
        """
        task.progress = max(0, min(100, progress))  # Ensure progress is between 0-100
        if status:
            task.status = status
        
        # Log progress updates
        app_logger.info(f"Task {task.task_id} progress: {task.progress}%, status: {task.status}")
    
    async def process_with_progress_tracking(self, file_path: str, task_id: str = None,
                                            verification_date_column: str = "AE",
                                            certificate_number_column: str = "AI") -> List[Report]:
        """
        Process an Excel file with progress tracking for background tasks.
        
        Args:
            file_path: Path to the Excel file to process
            task_id: Optional task ID for tracking
            verification_date_column: Column identifier for verification date (default 'AE' or 'Дата поверки')
            certificate_number_column: Column identifier for certificate number (default 'AI' or 'Наличие документа с отметкой о поверке (№ св-ва о поверке)')
            
        Returns:
            List of Report objects containing matched data
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # Create and initialize the processing task
        task = self.create_processing_task(file_path, task_id)
        task.status = ProcessingTaskStatus.PROCESSING
        
        try:
            app_logger.info(f"Starting processing of file {file_path} with progress tracking")
            
            # Parse the Excel file to get the total count for progress calculation
            excel_data_list = self.excel_parser.parse_excel_file(
                file_path, 
                verification_date_column, 
                certificate_number_column
            )
            total_records = len(excel_data_list)
            
            if total_records == 0:
                app_logger.warning(f"No valid records found in Excel file {file_path}")
                task.status = ProcessingTaskStatus.COMPLETED
                task.progress = 100
                return []
            
            reports = []
            
            # Process each Excel record with progress updates
            for idx, excel_record in enumerate(excel_data_list):
                # Calculate and update progress
                progress = int((idx / total_records) * 100) if total_records > 0 else 0
                await self.update_task_progress(task, progress)
                
                report = await self._process_single_record(excel_record, idx + 1)
                reports.append(report)
            
            # Final progress update
            await self.update_task_progress(task, 100, ProcessingTaskStatus.COMPLETED)
            app_logger.info(f"Completed processing of {total_records} records for task {task_id}")
            
            return reports
            
        except Exception as e:
            app_logger.error(f"Error in processing with progress tracking for task {task_id}: {e}")
            task.status = ProcessingTaskStatus.FAILED
            task.error_message = str(e)
            await self.update_task_progress(task, 100)  # Mark as complete with failed status
            raise
        finally:
            if task.status == ProcessingTaskStatus.PROCESSING:
                # If we get here without completing properly, mark as failed
                task.status = ProcessingTaskStatus.FAILED
                task.error_message = "Processing stopped unexpectedly"
    
    async def close(self):
        """Close resources used by the service"""
        await self.arshin_client.close()
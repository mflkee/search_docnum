import asyncio
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, cast

from src.config.settings import settings
from src.models.excel_data import ExcelRegistryData
from src.models.processing_task import ProcessingTask, ProcessingTaskStatus
from src.models.report import ProcessingStatus, Report
from src.services.arshin_client import ArshinClientService
from src.services.excel_parser import ExcelParserService
from src.utils.logging_config import app_logger
from src.utils.validators import validate_certificate_format


class DataProcessorService:
    """
    Service for processing Excel data and matching with Arshin registry.
    Handles the core logic of matching Excel records with Arshin data.
    """

    def __init__(self):
        self.excel_parser = ExcelParserService()
        self.arshin_client = ArshinClientService()
        self._concurrency_limit = max(1, settings.arshin_max_concurrent_requests)
        self._semaphore = asyncio.Semaphore(self._concurrency_limit)

    async def process_excel_file(self, file_path: str, task_id: Optional[str] = None,
                                verification_date_column: str = "Дата поверки",
                                certificate_number_column: str = "Наличие документа с отметкой о поверке (№ св-ва о поверке)",
                                sheet_name: str = "Перечень") -> list[Report]:
        """
        Process an Excel file by matching its records with Arshin registry data.

        Args:
            file_path: Path to the Excel file to process
            task_id: Optional task ID for tracking
            verification_date_column: Column header or Excel reference for verification date (default 'Дата поверки')
            certificate_number_column: Column header or Excel reference for certificate number (default 'Наличие документа с отметкой о поверке (№ св-ва о поверке)')
            sheet_name: Name of the sheet to parse (default 'Перечень')

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
                certificate_number_column,
                sheet_name
            )
            app_logger.info(f"Parsed {len(excel_data_list)} records from Excel file")

            if not excel_data_list:
                app_logger.warning(f"No valid records found in Excel file {file_path}")
                return []

            reports = await self._process_records_concurrently(excel_data_list)

            app_logger.info(f"Completed processing {len(reports)} records for task {task_id}")
            self._log_processing_statistics(reports)
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
                    verification_date=excel_record.verification_date.strftime("%Y-%m-%d") if excel_record.verification_date else "",
                    valid_date=None,
                    result_docnum=None,
                    source_certificate_number=excel_record.certificate_number,
                    certificate_updated=False,
                    processing_status=ProcessingStatus.INVALID_CERT_FORMAT,
                    excel_source_row=row_number
                )

            verification_year = excel_record.verification_date.year if excel_record.verification_date else None
            valid_until_year = excel_record.valid_until_date.year if excel_record.valid_until_date else None

            if verification_year is None and valid_until_year is not None:
                verification_year = max(valid_until_year - 1, 1900)

            if verification_year is None:
                app_logger.warning(
                    f"Unable to determine verification year for certificate {excel_record.certificate_number}; skipping record"
                )
                return Report(
                    arshin_id=None,
                    org_title=None,
                    mit_number=None,
                    mit_title=None,
                    mit_notation=None,
                    mi_number=excel_record.serial_number or "",
                    verification_date=excel_record.verification_date.strftime("%Y-%m-%d") if excel_record.verification_date else "",
                    valid_date=None,
                    result_docnum=None,
                    source_certificate_number=excel_record.certificate_number,
                    certificate_updated=False,
                    processing_status=ProcessingStatus.ERROR,
                    excel_source_row=row_number
                )

            # Query Arshin registry using the certificate number and year information
            arshin_record = await self.arshin_client.get_instrument_by_certificate(
                excel_record.certificate_number,
                verification_year,
                valid_until_year=valid_until_year
            )

            if arshin_record:
                normalized_source_doc = (excel_record.certificate_number or "").strip()
                normalized_result_doc = (arshin_record.result_docnum or "").strip()
                certificate_updated = bool(normalized_result_doc) and normalized_result_doc != normalized_source_doc

                # Successfully matched
                if certificate_updated:
                    app_logger.info(
                        f"Certificate updated for serial {excel_record.serial_number or ''}: "
                        f"{normalized_source_doc} -> {normalized_result_doc}"
                    )

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
                    source_certificate_number=excel_record.certificate_number,
                    certificate_updated=certificate_updated,
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
                    verification_date=excel_record.verification_date.strftime("%Y-%m-%d") if excel_record.verification_date else "",
                    valid_date=None,
                    result_docnum=None,
                    source_certificate_number=excel_record.certificate_number,
                    certificate_updated=False,
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
                verification_date=excel_record.verification_date.strftime("%Y-%m-%d") if excel_record.verification_date else "",
                valid_date=None,
                result_docnum=None,
                source_certificate_number=excel_record.certificate_number,
                certificate_updated=False,
                processing_status=ProcessingStatus.ERROR,
                excel_source_row=row_number
            )

    async def process_records_batch(self, excel_records: list[ExcelRegistryData]) -> list[Report]:
        """
        Process a batch of Excel records against the Arshin registry.

        Args:
            excel_records: List of ExcelRegistryData objects to process

        Returns:
            List of Report objects with the processing results
        """
        reports = await self._process_records_concurrently(excel_records)
        self._log_processing_statistics(reports)
        return reports

    async def _process_record_with_semaphore(self, index: int, excel_record: ExcelRegistryData) -> tuple[int, Report]:
        """
        Wrapper to process a single record with concurrency control.
        """
        async with self._semaphore:
            source_row_number = excel_record.source_row_number or (index + 2)
            report = await self._process_single_record(excel_record, source_row_number)
            return index, report

    async def _process_records_concurrently(
        self,
        excel_records: list[ExcelRegistryData],
        progress_callback: Optional[Callable[[int, int], Awaitable[None]]] = None
    ) -> list[Report]:
        """
        Process Excel records concurrently while respecting rate limits.

        Args:
            excel_records: List of records to process
            progress_callback: Optional coroutine called with (completed, total)

        Returns:
            List of Report objects ordered as input records
        """
        if not excel_records:
            return []

        app_logger.debug(
            f"Processing {len(excel_records)} records with concurrency limit {self._concurrency_limit}"
        )

        reports: list[Optional[Report]] = [None] * len(excel_records)
        tasks = [
            asyncio.create_task(self._process_record_with_semaphore(idx, record))
            for idx, record in enumerate(excel_records)
        ]

        completed = 0
        for coroutine in asyncio.as_completed(tasks):
            index, report = await coroutine
            reports[index] = report
            completed += 1

            if progress_callback:
                await progress_callback(completed, len(excel_records))

        # All slots must be filled
        return [cast(Report, report) for report in reports if report is not None]

    def _compute_processing_statistics(self, reports: list[Report]) -> dict[str, int]:
        """
        Compute processing statistics for the provided reports.

        Args:
            reports: List of processed Report instances

        Returns:
            Dictionary with aggregated statistics
        """
        total = len(reports)
        matched = sum(1 for r in reports if r.processing_status == ProcessingStatus.MATCHED)
        updated = sum(
            1
            for r in reports
            if r.processing_status == ProcessingStatus.MATCHED and bool(r.certificate_updated)
        )
        unchanged = sum(
            1
            for r in reports
            if r.processing_status == ProcessingStatus.MATCHED and r.certificate_updated is False
        )
        not_found = sum(1 for r in reports if r.processing_status == ProcessingStatus.NOT_FOUND)
        errors = sum(1 for r in reports if r.processing_status == ProcessingStatus.ERROR)
        invalid_format = sum(
            1 for r in reports if r.processing_status == ProcessingStatus.INVALID_CERT_FORMAT
        )

        return {
            "processed": total,
            "matched": matched,
            "updated": updated,
            "unchanged": unchanged,
            "not_found": not_found,
            "errors": errors,
            "invalid_format": invalid_format,
        }

    def _log_processing_statistics(self, reports: list[Report]) -> None:
        """
        Log aggregated processing statistics.

        Args:
            reports: List of processed Report instances
        """
        if not reports:
            app_logger.info("Processing summary: no records processed")
            return

        stats = self._compute_processing_statistics(reports)
        summary_message = (
            "Processing summary | обработано: {processed}, найдено: {matched} "
            "(обновлено: {updated}, без изменений: {unchanged}), не найдено: {not_found}, "
            "ошибки: {errors}, некорректный формат: {invalid_format}"
        ).format(**stats)
        app_logger.info(summary_message)

    def create_processing_task(self, file_path: str, task_id: Optional[str] = None) -> ProcessingTask:
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
            created_at=datetime.now(timezone.utc),
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

    async def process_with_progress_tracking(self, file_path: str, task_id: Optional[str] = None,
                                            verification_date_column: str = "Дата поверки",
                                            certificate_number_column: str = "Наличие документа с отметкой о поверке (№ св-ва о поверке)",
                                            sheet_name: str = "Перечень") -> list[Report]:
        """
        Process an Excel file with progress tracking for background tasks.

        Args:
            file_path: Path to the Excel file to process
            task_id: Optional task ID for tracking
            verification_date_column: Column header or Excel reference for verification date (default 'Дата поверки')
            certificate_number_column: Column header or Excel reference for certificate number (default 'Наличие документа с отметкой о поверке (№ св-ва о поверке)')
            sheet_name: Name of the sheet to parse (default 'Перечень')

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
                certificate_number_column,
                sheet_name
            )
            total_records = len(excel_data_list)

            if total_records == 0:
                app_logger.warning(f"No valid records found in Excel file {file_path}")
                task.status = ProcessingTaskStatus.COMPLETED
                task.progress = 100
                return []

            async def progress_callback(completed: int, total: int):
                progress = int((completed / total) * 100) if total > 0 else 0
                await self.update_task_progress(task, progress)

            reports = await self._process_records_concurrently(
                excel_data_list,
                progress_callback=progress_callback
            )

            await self.update_task_progress(task, 100, ProcessingTaskStatus.COMPLETED)
            app_logger.info(f"Completed processing of {total_records} records for task {task_id}")

            self._log_processing_statistics(reports)
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

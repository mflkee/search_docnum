import asyncio
import math
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, cast

from src.config.settings import settings
from src.models.arshin_record import ArshinRegistryRecord
from src.models.excel_data import ExcelRegistryData
from src.models.processing_task import ProcessingTask, ProcessingTaskStatus
from src.models.report import ProcessingStatus, Report
from src.services.arshin_client import ArshinClientService
from src.services.excel_parser import ExcelParserService
from src.utils.logging_config import app_logger
from src.utils.validators import validate_certificate_format


class DataProcessorService:
    """Core service orchestrating Excel parsing and Arшин lookups."""

    def __init__(self):
        self.excel_parser = ExcelParserService()
        self.arshin_client = ArshinClientService()
        self._concurrency_limit = max(1, settings.arshin_max_concurrent_requests)
        self._semaphore = asyncio.Semaphore(self._concurrency_limit)
        self._record_cache: dict[tuple[str, int, Optional[int]], Optional[ArshinRegistryRecord]] = {}

    async def process_excel_file(
        self,
        file_path: str,
        task_id: Optional[str] = None,
        verification_date_column: str = "Дата поверки",
        certificate_number_column: str = "Наличие документа с отметкой о поверке (№ св-ва о поверке)",
        sheet_name: str = "Перечень",
    ) -> list[Report]:
        """Process Excel synchronously (without task tracking)."""
        if not task_id:
            task_id = str(uuid.uuid4())

        app_logger.info(f"Starting processing of file {file_path} with task ID {task_id}")

        try:
            excel_data_list = self.excel_parser.parse_excel_file(
                file_path,
                verification_date_column,
                certificate_number_column,
                sheet_name,
            )
            app_logger.info(f"Parsed {len(excel_data_list)} records from Excel file")

            if not excel_data_list:
                app_logger.warning(f"No valid records found in Excel file {file_path}")
                return []

            reports = await self._process_records_concurrently(excel_data_list, progress_callback=None)
            self._log_processing_statistics(reports)
            return reports
        except Exception as exc:
            app_logger.error(f"Error processing Excel file {file_path}: {exc}")
            raise

    @staticmethod
    def _classify_report(report: Report) -> str:
        if report.processing_status == ProcessingStatus.NOT_FOUND:
            return "not_found"
        if report.processing_status in {ProcessingStatus.ERROR, ProcessingStatus.INVALID_CERT_FORMAT}:
            return "error"
        if report.processing_status == ProcessingStatus.MATCHED and bool(report.certificate_updated):
            return "updated"
        return "unchanged"

    async def _process_single_record(self, excel_record: ExcelRegistryData, row_number: int) -> Report:
        """Process a single Excel row against Arшин registry."""
        try:
            if not validate_certificate_format(excel_record.certificate_number):
                return Report(
                    arshin_id=None,
                    org_title=None,
                    mit_number=None,
                    mit_title=None,
                    mit_notation=None,
                    mi_number=excel_record.serial_number or "",
                    verification_date=(
                        excel_record.verification_date.strftime("%Y-%m-%d")
                        if excel_record.verification_date
                        else ""
                    ),
                    valid_date=(
                        excel_record.valid_until_date.strftime("%Y-%m-%d")
                        if excel_record.valid_until_date
                        else None
                    ),
                    result_docnum=excel_record.certificate_number,
                    source_certificate_number=excel_record.certificate_number,
                    certificate_updated=False,
                    processing_status=ProcessingStatus.INVALID_CERT_FORMAT,
                    excel_source_row=row_number,
                )

            current_year = datetime.now().year
            verification_year = excel_record.verification_date.year if excel_record.verification_date else None
            valid_until_year = excel_record.valid_until_date.year if excel_record.valid_until_date else None

            if verification_year is None and valid_until_year is not None:
                verification_year = max(valid_until_year - 1, 1900)

            if verification_year is None:
                app_logger.warning(
                    "Unable to determine verification year for certificate %s; skipping record",
                    excel_record.certificate_number,
                )
                return Report(
                    arshin_id=None,
                    org_title=None,
                    mit_number=None,
                    mit_title=None,
                    mit_notation=None,
                    mi_number=excel_record.serial_number or "",
                    verification_date=(
                        excel_record.verification_date.strftime("%Y-%m-%d")
                        if excel_record.verification_date
                        else ""
                    ),
                    valid_date=(
                        excel_record.valid_until_date.strftime("%Y-%m-%d")
                        if excel_record.valid_until_date
                        else None
                    ),
                    result_docnum=excel_record.certificate_number,
                    source_certificate_number=excel_record.certificate_number,
                    certificate_updated=False,
                    processing_status=ProcessingStatus.NOT_FOUND,
                    excel_source_row=row_number,
                )

            cache_key = (excel_record.certificate_number, verification_year, valid_until_year)
            if cache_key in self._record_cache:
                arshin_record = self._record_cache[cache_key]
            else:
                arshin_record = await self.arshin_client.get_instrument_by_certificate(
                    excel_record.certificate_number,
                    verification_year,
                    valid_until_year=valid_until_year,
                )
                self._record_cache[cache_key] = arshin_record

            skip_due_to_current_year = bool(
                excel_record.verification_date and excel_record.verification_date.year >= current_year
            )

            if arshin_record:
                normalized_source_doc = (excel_record.certificate_number or "").strip()
                normalized_result_doc = (arshin_record.result_docnum or "").strip()
                certificate_updated = bool(normalized_result_doc) and normalized_result_doc != normalized_source_doc

                arshin_verification_date = arshin_record.verification_date
                if (
                    skip_due_to_current_year
                    and arshin_verification_date
                    and excel_record.verification_date
                    and arshin_verification_date < excel_record.verification_date
                ):
                    certificate_updated = False
                    normalized_result_doc = normalized_source_doc

                return Report(
                    arshin_id=arshin_record.vri_id,
                    org_title=arshin_record.org_title,
                    mit_number=arshin_record.mit_number,
                    mit_title=arshin_record.mit_title,
                    mit_notation=arshin_record.mit_notation,
                    mi_number=arshin_record.mi_number,
                    verification_date=arshin_record.verification_date.strftime("%Y-%m-%d"),
                    valid_date=(
                        arshin_record.valid_date.strftime("%Y-%m-%d")
                        if arshin_record.valid_date
                        else (
                            excel_record.valid_until_date.strftime("%Y-%m-%d")
                            if excel_record.valid_until_date
                            else None
                        )
                    ),
                    result_docnum=normalized_result_doc,
                    source_certificate_number=excel_record.certificate_number,
                    certificate_updated=certificate_updated,
                    processing_status=ProcessingStatus.MATCHED,
                    excel_source_row=row_number,
                )

            return Report(
                arshin_id=None,
                org_title=None,
                mit_number=None,
                mit_title=None,
                mit_notation=None,
                mi_number=excel_record.serial_number or "",
                verification_date=(
                    excel_record.verification_date.strftime("%Y-%m-%d")
                    if excel_record.verification_date
                    else ""
                ),
                valid_date=(
                    excel_record.valid_until_date.strftime("%Y-%m-%d")
                    if excel_record.valid_until_date
                    else None
                ),
                result_docnum=None,
                source_certificate_number=excel_record.certificate_number,
                certificate_updated=False,
                processing_status=ProcessingStatus.NOT_FOUND,
                excel_source_row=row_number,
            )

        except Exception as exc:
            app_logger.error(
                "Error processing record with certificate %s: %s",
                excel_record.certificate_number,
                exc,
            )
            return Report(
                arshin_id=None,
                org_title=None,
                mit_number=None,
                mit_title=None,
                mit_notation=None,
                mi_number=excel_record.serial_number or "",
                verification_date=(
                    excel_record.verification_date.strftime("%Y-%m-%d")
                    if excel_record.verification_date
                    else ""
                ),
                valid_date=(
                    excel_record.valid_until_date.strftime("%Y-%m-%d")
                    if excel_record.valid_until_date
                    else None
                ),
                result_docnum=None,
                source_certificate_number=excel_record.certificate_number,
                certificate_updated=False,
                processing_status=ProcessingStatus.ERROR,
                excel_source_row=row_number,
            )

    async def process_records_batch(self, excel_records: list[ExcelRegistryData]) -> list[Report]:
        reports = await self._process_records_concurrently(excel_records, progress_callback=None)
        self._log_processing_statistics(reports)
        return reports

    async def _process_record_with_semaphore(
        self,
        index: int,
        excel_record: ExcelRegistryData,
    ) -> tuple[int, Report]:
        async with self._semaphore:
            source_row_number = excel_record.source_row_number or (index + 2)
            report = await self._process_single_record(excel_record, source_row_number)
            return index, report

    async def _process_records_concurrently(
        self,
        excel_records: list[ExcelRegistryData],
        progress_callback: Optional[Callable[[int, int, Report], Awaitable[None]]],
    ) -> list[Report]:
        if not excel_records:
            return []

        app_logger.debug(
            "Processing %d records with concurrency limit %d",
            len(excel_records),
            self._concurrency_limit,
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
                await progress_callback(completed, len(excel_records), report)

        return [cast(Report, report) for report in reports if report is not None]

    def _compute_processing_statistics(self, reports: list[Report]) -> dict[str, int]:
        total = len(reports)
        updated = sum(
            1
            for r in reports
            if r.processing_status == ProcessingStatus.MATCHED and bool(r.certificate_updated)
        )
        unchanged = sum(
            1
            for r in reports
            if r.processing_status == ProcessingStatus.MATCHED and not r.certificate_updated
        )
        not_found = sum(1 for r in reports if r.processing_status == ProcessingStatus.NOT_FOUND)
        errors = sum(1 for r in reports if r.processing_status == ProcessingStatus.ERROR)
        invalid_format = sum(
            1 for r in reports if r.processing_status == ProcessingStatus.INVALID_CERT_FORMAT
        )

        return {
            "processed": total,
            "updated": updated,
            "unchanged": unchanged,
            "not_found": not_found,
            "errors": errors,
            "invalid_format": invalid_format,
        }

    def _log_processing_statistics(self, reports: list[Report]) -> None:
        if not reports:
            app_logger.info("Processing summary: no records processed")
            return

        stats = self._compute_processing_statistics(reports)
        app_logger.info(
            "Processing summary | обработано: %(processed)s, обновлено: %(updated)s, без изменений: %(unchanged)s, "
            "не найдено: %(not_found)s, ошибки: %(errors)s, некорректный формат: %(invalid_format)s",
            stats,
        )

    def compute_processing_statistics(self, reports: list[Report]) -> dict[str, int]:
        return self._compute_processing_statistics(reports)

    def create_processing_task(self, file_path: str, task_id: Optional[str] = None) -> ProcessingTask:
        if not task_id:
            task_id = str(uuid.uuid4())

        return ProcessingTask(
            task_id=task_id,
            status=ProcessingTaskStatus.PENDING,
            progress=0,
            created_at=datetime.now(timezone.utc),
            file_path=file_path,
        )

    async def update_task_progress(
        self,
        task: ProcessingTask,
        progress: int,
        status: Optional[ProcessingTaskStatus] = None,
    ) -> None:
        task.progress = max(0, min(100, progress))
        if status:
            task.status = status
        app_logger.debug("Task %s progress: %d%% (%s)", task.task_id, task.progress, task.status.value)

    async def process_with_progress_tracking(
        self,
        file_path: str,
        task_id: Optional[str] = None,
        verification_date_column: str = "Дата поверки",
        certificate_number_column: str = "Наличие документа с отметкой о поверке (№ св-ва о поверке)",
        sheet_name: str = "Перечень",
    ) -> list[Report]:
        if not task_id:
            task_id = str(uuid.uuid4())

        task = self.create_processing_task(file_path, task_id)
        task.status = ProcessingTaskStatus.PROCESSING

        try:
            app_logger.info(f"Starting processing of file {file_path} with progress tracking")

            excel_data_list = self.excel_parser.parse_excel_file(
                file_path,
                verification_date_column,
                certificate_number_column,
                sheet_name,
            )

            total_records = len(excel_data_list)
            task.total_records = total_records

            if total_records == 0:
                app_logger.warning(f"No valid records found in Excel file {file_path}")
                task.status = ProcessingTaskStatus.COMPLETED
                task.progress = 100
                task.summary = {"processed": 0, "updated": 0, "unchanged": 0, "not_found": 0}
                return []

            summary_running = {
                "processed": 0,
                "updated": 0,
                "unchanged": 0,
                "not_found": 0,
            }

            async def progress_callback(completed: int, total: int, report: Report) -> None:
                summary_running["processed"] = completed
                status_kind = self._classify_report(report)
                if status_kind == "updated":
                    summary_running["updated"] += 1
                elif status_kind == "unchanged":
                    summary_running["unchanged"] += 1
                elif status_kind == "not_found":
                    summary_running["not_found"] += 1

                task.processed_records = completed
                task.summary = summary_running.copy()

                progress = 0
                if total > 0:
                    progress = math.ceil((completed / total) * 100) if completed < total else 100

                await self.update_task_progress(task, progress)

            reports = await self._process_records_concurrently(
                excel_data_list,
                progress_callback=progress_callback,
            )

            final_stats = self._compute_processing_statistics(reports)
            task.summary = {
                "processed": final_stats.get("processed", 0),
                "updated": final_stats.get("updated", 0),
                "unchanged": final_stats.get("unchanged", 0),
                "not_found": final_stats.get("not_found", 0),
            }
            task.processed_records = total_records

            await self.update_task_progress(task, 100, ProcessingTaskStatus.COMPLETED)
            self._log_processing_statistics(reports)
            return reports

        except Exception as exc:
            app_logger.error("Error in processing with progress tracking for task %s: %s", task_id, exc)
            task.status = ProcessingTaskStatus.FAILED
            task.error_message = str(exc)
            task.summary = task.summary or {"processed": 0, "updated": 0, "unchanged": 0, "not_found": 0}
            await self.update_task_progress(task, 100)
            raise
        finally:
            if task.status == ProcessingTaskStatus.PROCESSING:
                task.status = ProcessingTaskStatus.FAILED
                task.error_message = "Processing stopped unexpectedly"

    async def close(self) -> None:
        await self.arshin_client.close()

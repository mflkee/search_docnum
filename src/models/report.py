from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ProcessingStatus(str, Enum):
    MATCHED = "MATCHED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"
    INVALID_CERT_FORMAT = "INVALID_CERT_FORMAT"


class Report(BaseModel):
    """
    Structured output containing matched data from both sources plus processing status.
    """
    arshin_id: Optional[str] = None  # ID in Arshin registry (from matched record, null if not found)
    org_title: Optional[str] = None  # Organization name (from matched record, null if not found)
    mit_number: Optional[str] = None  # Type registration number (from matched record, null if not found)
    mit_title: Optional[str] = None  # Type name (from matched record, null if not found)
    mit_notation: Optional[str] = None  # Type notation (from matched record, null if not found)
    mi_number: str  # Serial number (from original Excel data)
    verification_date: str  # Verification date (from original Excel data)
    valid_date: Optional[str] = None  # Valid until date (from matched record, null if not found)
    result_docnum: Optional[str] = None  # Certificate number (from matched record, null if not found)
    source_certificate_number: Optional[str] = None  # Certificate number supplied in the original Excel
    certificate_updated: Optional[bool] = None  # Flag indicating whether certificate number changed after lookup
    processing_status: ProcessingStatus  # Status of matching process (MATCHED, NOT_FOUND, ERROR, INVALID_CERT_FORMAT)
    excel_source_row: int  # Row number in original Excel file for reference

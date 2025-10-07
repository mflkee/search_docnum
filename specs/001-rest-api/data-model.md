# Data Model: Система автоматизации реестра СИ

## Overview
This document defines the data models for the measurement instruments registry synchronization system, incorporating clarifications about certificate validation, handling multiple records, and missing records.

## Core Entities

### ExcelRegistryData
Represents input data from Excel files containing measurement instruments information.

**Attributes:**
- `verification_date`: datetime - Verification date (formats: DD.MM.YYYY, YYYY-MM-DD)
- `certificate_number`: str - Certificate number from column AI, validated format
- `device_name`: Optional[str] - Device name (from Excel context)
- `serial_number`: Optional[str] - Serial number (from Excel context)
- `additional_data`: Dict[str, Any] - Additional columns from Excel file

**Validation Rules:**
- `verification_date` must be in recognized format
- `certificate_number` must not be empty and must match expected pattern
- Date formats must be properly parsed
- Certificate number format validated before processing

### ArshinRegistryRecord
Represents records from Arshin API containing instrument details.

**Attributes:**
- `vri_id`: str - ID in Arshin registry
- `org_title`: str - Verifying organization name
- `mit_number`: str - Registration number of instrument type
- `mit_title`: str - Name of instrument type
- `mit_notation`: str - Notation of instrument type
- `mi_number`: str - Serial number of instrument
- `verification_date`: datetime - Verification date
- `valid_date`: datetime - Valid until date
- `result_docnum`: str - Certificate number
- `record_date`: datetime - Date associated with this record for comparison

**Validation Rules:**
- All fields must have values when record exists in Arshin
- Date fields must be valid
- ID fields must follow Arshin registry format
- `record_date` used to select most recent when multiple records found

### ProcessingTask
Represents an asynchronous processing job with status tracking.

**Attributes:**
- `task_id`: str - Unique identifier for the task
- `status`: str - Current status (PENDING, PROCESSING, COMPLETED, FAILED)
- `progress`: int - Progress percentage (0-100)
- `created_at`: datetime - When task was created
- `completed_at`: Optional[datetime] - When task was completed
- `file_path`: str - Path to input file
- `result_path`: Optional[str] - Path to output report
- `error_message`: Optional[str] - Error if task failed

**State Transitions:**
```
PENDING -> PROCESSING -> COMPLETED
              |
              v
            FAILED
```

**Validation Rules:**
- `task_id` must be unique
- `status` must be one of the allowed values
- `progress` must be between 0-100

### Report
Structured output containing matched data from both sources plus processing status.

**Attributes:**
- `arshin_id`: Optional[str] - ID in Arshin registry (from matched record, null if not found)
- `org_title`: Optional[str] - Organization name (from matched record, null if not found)
- `mit_number`: Optional[str] - Type registration number (from matched record, null if not found)
- `mit_title`: Optional[str] - Type name (from matched record, null if not found)
- `mit_notation`: Optional[str] - Type notation (from matched record, null if not found)
- `mi_number`: str - Serial number (from original Excel data)
- `verification_date`: str - Verification date (from original Excel data)
- `valid_date`: Optional[str] - Valid until date (from matched record, null if not found)
- `result_docnum`: Optional[str] - Certificate number (from matched record, null if not found)
- `processing_status`: str - Status of matching process (MATCHED, NOT_FOUND, ERROR, INVALID_CERT_FORMAT)
- `excel_source_row`: int - Row number in original Excel file for reference

**Additional Validation Rules:**
- When `processing_status` is 'NOT_FOUND', all Arshin-related fields (arshin_id, org_title, etc.) should be null
- When `processing_status` is 'INVALID_CERT_FORMAT', appropriate error details should be captured

## Relationships

- One `ProcessingTask` manages the processing of one Excel file containing multiple `ExcelRegistryData` records
- One `ExcelRegistryData` record may match zero or one `ArshinRegistryRecord` (when multiple matches, the most recent is selected)
- Multiple `ExcelRegistryData` records from one `ProcessingTask` produce multiple `Report` entries
- When no `ArshinRegistryRecord` matches an `ExcelRegistryData` record, a `Report` entry is still created with 'NOT_FOUND' status
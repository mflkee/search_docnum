# Feature Specification: Система для автоматической синхронизации данных реестра средств измерений с государственным реестром Аршин

**Feature Branch**: `001-rest-api`  
**Created**: 2025-10-07  
**Status**: Draft  
**Input**: User description: "Система для автоматической синхронизации данных реестра средств измерений с государственным реестром Аршин через REST API"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Excel File Upload and Processing via Web Interface (Priority: P1)

An Operator uploads an Excel file containing measurement instruments registry data through the web interface. The system processes this data to synchronize with the state Arshin registry via API and returns a structured report.

**Why this priority**: This is the core functionality of the system - without the ability to process Excel files and sync with Arshin, the system has no value.

**Independent Test**: Can be fully tested by uploading an Excel file with known data through the web interface and verifying that the system returns a report with matched records from Arshin registry.

**Acceptance Scenarios**:

1. **Given** an operator has an Excel file with measurement instruments data, **When** they upload it through the web interface, **Then** the system returns a task ID and begins processing in the background
2. **Given** a processed Excel file, **When** the operator requests the results through the web interface, **Then** the system returns a report with matched Arshin registry data

---

### User Story 2 - Integration with External Systems (Priority: P2)

An External System sends an Excel file for processing, and receives results via status polling.

**Why this priority**: This enables integration with other business systems and automates the synchronization process.

**Independent Test**: Can be fully tested by sending a file through the API interface and verifying the system processes it and makes results available via the status and results endpoints.

**Acceptance Scenarios**:

1. **Given** an external system has measurement data, **When** it sends the data through the API interface, **Then** the system returns a task ID and processes the data asynchronously

### Edge Cases

- What happens when the file exceeds the maximum allowed size (100MB)?
- How does the system handle files with invalid Excel format or corrupted data?
- How does the system handle situations when the Arshin API is temporarily unavailable?
- What if the Excel file contains date formats that don't match expected patterns?
- What if the Arshin API returns multiple matching records for the same certificate number?
- What if a certificate number from Excel file is not found in the Arshin registry?
- What if certificate number format is invalid?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST accept Excel file uploads through a web interface
- **FR-002**: System MUST process Excel files in formats .xlsx and .xls with auto-detection of structure
- **FR-003**: System MUST parse specific columns (AE: verification date, AI: certificate number) from Excel files
- **FR-004**: System MUST validate input data including mandatory fields and date formats
- **FR-005**: System MUST search Arshin registry using multi-stage verification process
- **FR-006**: System MUST extract specific fields from Arshin registry (ID, organization, type registration number, type name, notation, serial number, verification date, validity date, certificate number)
- **FR-007**: System MUST implement request limiting to prevent overloading external services
- **FR-008**: System MUST include retry logic for temporary external service failures
- **FR-009**: System MUST generate structured reports in Excel format with matched Arshin data
- **FR-010**: System MUST provide endpoints for file upload, status checking, and result retrieval
- **FR-011**: System MUST support asynchronous processing with task ID return for tracking
- **FR-012**: System MUST validate certificate number format before querying Arshin API
- **FR-013**: System MUST validate uploaded files for security purposes
- **FR-014**: System MUST provide progress tracking for long-running operations
- **FR-015**: System MUST log operations for audit purposes
- **FR-016**: When multiple Arshin records match, system MUST select the most recent record by date
- **FR-017**: When Arshin record is not found, system MUST include the record with null/empty Arshin data fields and mark as 'NOT_FOUND'
- **FR-018**: System MUST query the external Arshin API for fresh data without caching

### Key Entities

- **ExcelRegistryData**: Input data from Excel files containing measurement instruments information (verification date, certificate number, device name, serial number)
- **ArshinRegistryRecord**: Records from Arshin API containing instrument details (vri_id, organization, type registration number, type name, notation, serial number, verification date, validity date, certificate number)
- **ProcessingTask**: Represents an asynchronous processing job with status tracking
- **Report**: Structured output containing matched data from both sources plus processing status

## Clarifications

### Session 2025-10-07

- Q: How should the system handle cases when the Arshin API returns multiple records for the same criteria? → A: Select the most recent record (by date) when multiple matches found
- Q: How should the system handle cases when a certificate number from the Excel file is not found in the Arshin registry? → A: Include the record with null/empty Arshin data fields and mark as 'NOT_FOUND'
- Q: Should the system validate the format of certificate numbers before attempting to query the Arshin API? → A: Yes, validate format and reject invalid formats before API query
- Q: Should the system implement caching for Arshin API responses? → A: No, always query the external API for fresh data
- Q: Do we need the CLI interface since we have a web interface? → A: CLI interface is not needed as web interface will be the primary interaction method

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Users can upload and initiate processing of Excel files up to 100MB within 30 seconds
- **SC-002**: System can process at least 10 concurrent files without degradation in performance
- **SC-003**: 95% of valid Excel files with correct structure are successfully processed and matched with Arshin registry within 5 minutes
- **SC-004**: Operators can retrieve processing results with 99% reliability within 10 seconds of completion
- **SC-005**: System response time for status queries is under 2 seconds 95% of the time
- **SC-006**: System completes processing of a 50MB Excel file within 2 minutes on standard hardware
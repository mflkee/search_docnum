# OpenAPI Contract for Arshin Registry Synchronization API

## Overview
API specification for the system that synchronizes measurement instruments registry data with the state Arshin registry.

## API Endpoints

### File Upload
**Endpoint**: `POST /api/v1/upload`
**Description**: Upload an Excel file for processing and initiate background task.

**Request**:
- Content-Type: multipart/form-data
- Form field: `file` (required) - Excel file (.xlsx or .xls)

**Responses**:
- `202 Accepted`: File uploaded successfully, processing started
  ```json
  {
    "task_id": "string",
    "status": "PENDING",
    "message": "File uploaded and processing started"
  }
  ```
- `400 Bad Request`: Invalid file format or validation error
  ```json
  {
    "error": "string",
    "details": "string"
  }
  ```
- `413 Payload Too Large`: File exceeds size limit
- `422 Unprocessable Entity`: File format or content validation failed, including invalid certificate number formats

### Task Status
**Endpoint**: `GET /api/v1/status/{task_id}`
**Description**: Check the processing status of a task.

**Path Parameters**:
- `task_id`: string (required) - ID of the processing task

**Responses**:
- `200 OK`: Task status retrieved
  ```json
  {
    "task_id": "string",
    "status": "PENDING|PROCESSING|COMPLETED|FAILED",
    "progress": 0,
    "result_available": false,
    "created_at": "2025-10-07T10:00:00Z",
    "completed_at": "2025-10-07T10:05:00Z"
  }
  ```
- `404 Not Found`: Task ID not found

### Results Download
**Endpoint**: `GET /api/v1/results/{task_id}`
**Description**: Download the processed results if available.

**Path Parameters**:
- `task_id`: string (required) - ID of the processing task

**Responses**:
- `200 OK`: File ready for download (returns Excel file)
- `404 Not Found`: Task ID not found
- `409 Conflict`: Task not completed or failed

### Health Check
**Endpoint**: `GET /api/v1/health`
**Description**: Check the health status of the service.

**Responses**:
- `200 OK`: Service is healthy
  ```json
  {
    "status": "healthy",
    "timestamp": "2025-10-07T10:00:00Z"
  }
  ```

## Web Interface Endpoints

### Upload Page
**Endpoint**: `GET /`
**Description**: Main page with file upload interface.

**Responses**:
- `200 OK`: HTML page with drag-and-drop upload interface

### Status Page
**Endpoint**: `GET /status/{task_id}`
**Description**: Page showing processing status with progress updates.

**Path Parameters**:
- `task_id`: string (required) - ID of the processing task

**Responses**:
- `200 OK`: HTML page with status updates
- `404 Not Found`: Task ID not found

### Results Page
**Endpoint**: `GET /results/{task_id}`
**Description**: Page with download link for processed results.

**Path Parameters**:
- `task_id`: string (required) - ID of the processing task

**Responses**:
- `200 OK`: HTML page with download link
- `404 Not Found`: Task ID not found
- `409 Conflict`: Task not completed or failed
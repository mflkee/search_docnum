# Quickstart Guide: Система автоматизации реестра СИ

## Overview
This guide provides instructions on how to get started with the measurement instruments registry synchronization system, focusing on the web interface as the primary interaction method (CLI interface has been removed per clarifications).

## Prerequisites
- Python 3.13+
- Docker and Docker Compose (for containerized deployment)
- Excel file with measurement instruments registry data (formats: .xlsx, .xls)

## Installation

### Option 1: Local Development
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements/dev.txt
   ```

### Option 2: Docker
1. Clone the repository
2. Build and run with Docker Compose:
   ```bash
   docker-compose up --build
   ```

## Usage

### Web Interface (Primary Method)

#### 1. Starting the Web Server
```bash
# If running locally
uvicorn src.api.main:app --reload

# If using Docker
docker-compose up
```

#### 2. Uploading a File via Web Interface
1. Navigate to `http://localhost:8000` in your browser
2. Use the drag-and-drop area or click to browse for your Excel file
3. The system will upload the file and start processing in the background
4. You'll receive a task ID and can track progress on the status page

#### 3. Tracking Processing Status
- On the status page, enter your task ID or click on recent tasks
- The page will automatically update with processing progress
- When complete, a download button will appear for your results

#### 4. Downloading Results
- Once processing is complete, the results page will show a download link
- Click to download the Excel file with matched Arshin registry data

### API Interface (For External Systems)

#### 1. Uploading a File via API
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "accept: application/json" \
  -F "file=@path/to/your/excel_file.xlsx"
```

#### 2. Checking Processing Status
```bash
curl -X GET "http://localhost:8000/api/v1/status/{task_id}"
```

#### 3. Downloading Results via API
```bash
curl -X GET "http://localhost:8000/api/v1/results/{task_id}" -O
```

## Configuration

The system uses environment variables for configuration:
- `ARSHIN_API_BASE_URL`: Base URL for Arshin registry API
- `MAX_FILE_SIZE`: Maximum upload size in bytes (default: 100MB)
- `RATE_LIMIT_REQUESTS`: Number of requests allowed per period (default: 10)
- `RATE_LIMIT_PERIOD`: Time period in seconds (default: 60)
- `CELERY_BROKER_URL`: Broker URL for Celery tasks (default: redis://localhost:6379)

## File Format Requirements

The system expects Excel files with the following columns:
- Column AE: Verification date (formats: DD.MM.YYYY, YYYY-MM-DD)
- Column AI: Certificate number (format will be validated)
- Additional columns for context (device name, serial number, etc.)

## Troubleshooting

- If you get "Payload Too Large" errors, ensure your file is under 100MB
- If you get validation errors for certificate numbers, check the format
- For API timeout issues, check that the Arshin registry API is accessible
- For file parsing errors, verify Excel format and column structure

## Next Steps

1. Review the API documentation at `/docs` when running the web server
2. Check out the full implementation plan in `specs/001-rest-api/plan.md`
3. Look at the data models in `specs/001-rest-api/data-model.md`
4. Review the API contracts in `specs/001-rest-api/contracts/`
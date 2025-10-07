# Implementation Plan: Система для автоматической синхронизации данных реестра средств измерений с государственным реестром Аршин

**Branch**: `001-rest-api` | **Date**: 2025-10-07 | **Spec**: /home/mflkee/project/search_docnum/specs/001-rest-api/spec.md
**Input**: Feature specification from `/specs/001-rest-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implementation of a system for automatic synchronization of measurement instruments registry data with the state Arshin registry via API. The system will process Excel files (uploaded through a web interface) containing verification data, match records with the Arshin registry using a two-stage verification process, and generate structured reports. The solution will include a web API with HTML interface for file uploads and status tracking, and an API for external system integration, following the project's constitution principles of clean architecture, comprehensive testing, and containerization. The system will validate certificate number formats, handle cases where records are not found in Arshin registry, always query fresh data from the API without caching, and select the most recent record when multiple matches are found.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13+  
**Primary Dependencies**: FastAPI, pandas, httpx, pytest, Docker, uv, celery (or FastAPI BackgroundTasks), Jinja2 (for templating), Starlette (for web templates)
**Storage**: File-based storage for Excel files and reports (local filesystem or volume mount), Redis for task queue (if using Celery)
**Testing**: pytest (with comprehensive test coverage >90%), responses for HTTP mocking, pytest-asyncio for async tests, pytest-playwright for UI testing
**Target Platform**: Linux server (containerized with Docker)  
**Project Type**: Single project with clean architecture - web API + HTML interface (no CLI interface)
**Performance Goals**: Process 100MB Excel files within 5 minutes; handle 10+ concurrent file uploads; respond to status queries within 2 seconds
**Constraints**: Asynchronous operations, proper error handling, data validation, rate limiting for external APIs, file size limits up to 100MB, web interface with drag-and-drop and AJAX updates, no CLI interface as per clarifications
**Scale/Scope**: Synchronization system for measurement instruments registry processing individual files up to 100MB with concurrent processing support and HTML web interface, with two-stage verification against Arshin API, certificate format validation, and handling of multiple or missing records

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Modern Python Stack**: PASS - Using FastAPI, pandas, httpx as required by constitution
**Comprehensive Test Coverage**: PASS - Using pytest with >90% coverage requirement
**Containerization Through Docker**: PASS - Planning Docker containerization
**Clean Architecture with Separation of Concerns**: PASS - Planning layered architecture with models, services, API, web interface layers
**Error Handling and Data Validation**: PASS - Planning comprehensive validation and error handling including certificate format validation
**Asynchronous API Requests**: PASS - Planning async operations with httpx for Arshin API calls

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── __init__.py
│   ├── excel_data.py          # Data models for Excel file data
│   ├── arshin_record.py       # Data models for Arshin API responses
│   ├── processing_task.py     # Models for processing tasks
│   └── report.py              # Models for report generation
├── services/
│   ├── __init__.py
│   ├── excel_parser.py        # Service for parsing Excel files
│   ├── arshin_client.py       # Async client for Arshin API
│   ├── data_processor.py      # Service for processing data and matching logic
│   ├── report_generator.py    # Service for generating Excel reports
│   └── file_validator.py      # Service for file validation and security
├── api/
│   ├── __init__.py
│   ├── main.py               # FastAPI app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py         # File upload endpoint
│   │   ├── status.py         # Task status endpoint
│   │   ├── results.py        # Results download endpoint
│   │   ├── health.py         # Health check endpoint
│   │   └── web_interface.py  # Web interface routes (HTML pages)
│   └── middleware/
│       ├── __init__.py
│       └── error_handler.py  # Error handling middleware
├── templates/
│   ├── __init__.py
│   ├── base.html             # Base HTML template
│   ├── upload.html           # File upload page with drag-and-drop
│   ├── status.html           # Task status page with progress updates
│   └── results.html          # Results download page
├── static/
│   ├── css/
│   │   └── style.css         # CSS styling (possibly Bootstrap based)
│   ├── js/
│   │   ├── main.js           # JavaScript for AJAX requests and UI interactions
│   │   └── upload.js         # JavaScript for upload functionality
│   └── images/
│       └── logo.png          # Optional images
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration settings
├── utils/
│   ├── __init__.py
│   ├── validators.py         # Validation utilities
│   ├── date_utils.py         # Date parsing utilities
│   ├── logging_config.py     # Logging configuration
│   └── web_utils.py          # Web interface utilities
└── __init__.py

tests/
├── unit/
│   ├── __init__.py
│   ├── test_excel_parser.py
│   ├── test_arshin_client.py
│   ├── test_data_processor.py
│   └── test_report_generator.py
├── integration/
│   ├── __init__.py
│   ├── test_api_endpoints.py
│   ├── test_web_interface.py
│   └── test_external_integration.py  # Tests for external system integration
├── contract/
│   ├── __init__.py
│   └── test_arshin_api.py    # Contract tests for external API
├── ui/
│   ├── __init__.py
│   └── test_web_ui.py        # UI tests for web interface
└── conftest.py               # pytest configuration

alembic/
├── env.py
├── script.py.mako
└── versions/
    └── README

docker/
├── Dockerfile
├── docker-compose.yml
└── docker-compose.prod.yml

docs/
└── quickstart.md             # Quickstart guide

requirements/
├── base.txt
├── dev.txt
└── prod.txt
```

**Structure Decision**: Single project structure with clean architecture following the principles in the constitution. The architecture is divided into models (data structures), services (business logic), API (web interface), templates (HTML views), static files (CSS/JS), config (settings), and utils (helpers). Tests are organized by type (unit, integration, contract, UI) with proper separation of concerns. The web interface includes HTML templates with drag-and-drop upload, status tracking with AJAX updates, and result download functionality. CLI interface has been removed as per clarifications. The system handles two-stage verification against Arshin API, certificate format validation, and special cases for multiple or missing records.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

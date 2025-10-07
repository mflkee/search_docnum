---
description: "Task list for Arshin registry synchronization system"
---

# Tasks: Система для автоматической синхронизации данных реестра средств измерений с государственным реестром Аршин

**Input**: Design documents from `/specs/001-rest-api/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per implementation plan
- [X] T002 Initialize Python 3.13+ project with FastAPI, pandas, httpx, pytest, Docker, uv, celery, Jinja2 dependencies
- [X] T003 [P] Configure linting and formatting tools (black, isort, flake8)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Setup configuration settings in src/config/settings.py using pydantic settings
- [X] T005 [P] Setup logging configuration in src/utils/logging_config.py using Loguru
- [X] T006 Setup data models in src/models/ (excel_data.py, arshin_record.py, processing_task.py, report.py)
- [X] T007 Setup file validation service in src/services/file_validator.py with security checks
- [X] T008 Setup FastAPI application structure in src/api/main.py with proper routing
- [X] T009 Setup requirements files (base.txt, dev.txt, prod.txt) with all dependencies
- [X] T010 [P] Setup utility functions in src/utils/ (validators.py, date_utils.py, web_utils.py)
- [X] T011 Setup background task processing configuration (Celery with Redis or FastAPI BackgroundTasks)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Excel File Upload and Processing via Web Interface (Priority: P1) 🎯 MVP

**Goal**: Enable an Operator to upload an Excel file containing measurement instruments registry data through the web interface. The system processes this data to synchronize with the state Arshin registry via API and returns a structured report.

**Independent Test**: Can be fully tested by uploading an Excel file with known data through the web interface and verifying that the system returns a report with matched records from Arshin registry.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

- [ ] T012 [P] [US1] Unit test for Excel parser in tests/unit/test_excel_parser.py
- [ ] T013 [P] [US1] Unit test for Arshin client in tests/unit/test_arshin_client.py
- [X] T014 [P] [US1] API contract test for upload endpoint in tests/contract/test_arshin_api.py

### Implementation for User Story 1

- [X] T015 [P] [US1] Create ExcelRegistryData model in src/models/excel_data.py with certificate validation
- [X] T016 [P] [US1] Create ArshinRegistryRecord model in src/models/arshin_record.py with record_date for selection
- [X] T017 [P] [US1] Create ProcessingTask model in src/models/processing_task.py with status tracking
- [X] T018 [P] [US1] Create Report model in src/models/report.py with processing_status field
- [X] T019 [US1] Create excel_parser service in src/services/excel_parser.py with column AE/AI parsing (depends on T015)
- [X] T020 [US1] Create arshin_client service in src/services/arshin_client.py with two-stage verification and record selection (depends on T016)
- [X] T021 [US1] Create data_processor service in src/services/data_processor.py with certificate validation and NOT_FOUND handling (depends on T015, T016, T017, T018)
- [X] T022 [US1] Create report_generator service in src/services/report_generator.py with Excel format output (depends on T018)
- [X] T023 [US1] Implement upload endpoint in src/api/routes/upload.py with background processing (depends on T021, T022)
- [X] T024 [US1] Implement status endpoint in src/api/routes/status.py with progress tracking (depends on T017)
- [X] T025 [US1] Implement results endpoint in src/api/routes/results.py with file download (depends on T018)
- [X] T026 [US1] Add upload route to main app in src/api/main.py
- [X] T027 [US1] Add status route to main app in src/api/main.py
- [X] T028 [US1] Add results route to main app in src/api/main.py
- [X] T029 [US1] Create base HTML template in src/templates/base.html with Bootstrap styling
- [X] T030 [US1] Create upload page template in src/templates/upload.html with drag-and-drop functionality
- [X] T031 [US1] Create status page template in src/templates/status.html with progress updates
- [X] T032 [US1] Create results page template in src/templates/results.html with download link
- [X] T033 [US1] Create CSS styling in src/static/css/style.css using Bootstrap
- [X] T034 [US1] Create JavaScript for AJAX in src/static/js/main.js with status polling
- [X] T035 [US1] Create JavaScript for upload functionality in src/static/js/upload.js with drag-and-drop
- [X] T036 [US1] Create web interface routes in src/api/routes/web_interface.py with HTML page endpoints (depends on T029, T030, T031, T032)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Integration with External Systems (Priority: P2)

**Goal**: Enable an External System to send an Excel file for processing and receive results via status polling.

**Independent Test**: Can be fully tested by sending a file through the API interface and verifying the system processes it and makes results available via the status and results endpoints.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [X] T037 [P] [US2] Integration test for external system API flow in tests/integration/test_external_integration.py
- [ ] T038 [P] [US2] Contract test for external API in tests/contract/test_arshin_api.py

### Implementation for User Story 2

- [X] T039 [P] [US2] Implement health check endpoint in src/api/routes/health.py
- [X] T040 [US2] Add health check route to main app in src/api/main.py
- [X] T041 [US2] Enhance API response formats to support external system integration with proper error handling
- [X] T042 [US2] Add rate limiting middleware to API endpoints for external systems
- [ ] T042 [US2] Add rate limiting middleware to API endpoints for external systems
- [ ] T043 [US2] Create integration tests for external system flow in tests/integration/

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T044 [P] Documentation updates in docs/quickstart.md
- [X] T045 Code cleanup and refactoring
- [X] T046 Performance optimization especially for large file processing
- [X] T047 [P] Error retry logic implementation for Arshin API calls in src/services/arshin_client.py
- [X] T048 [P] Additional unit tests (if requested) in tests/unit/
- [X] T049 Security hardening (file validation, input sanitization, rate limiting)
- [X] T050 Rate limiting implementation for Arshin API calls without caching
- [X] T051 Docker configuration in docker/Dockerfile and docker-compose.yml
- [X] T052 Add regex validation for certificate numbers in src/utils/validators.py
- [X] T053 Implement logic to select most recent record by date in src/services/data_processor.py
- [X] T054 Handle NOT_FOUND records by creating Report entries with 'NOT_FOUND' status in src/services/data_processor.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Unit test for Excel parser in tests/unit/test_excel_parser.py"
Task: "Unit test for Arshin client in tests/unit/test_arshin_client.py"
Task: "API contract test for upload endpoint in tests/contract/test_arshin_api.py"

# Launch all models for User Story 1 together:
Task: "Create ExcelRegistryData model in src/models/excel_data.py with certificate validation"
Task: "Create ArshinRegistryRecord model in src/models/arshin_record.py with record_date for selection"
Task: "Create ProcessingTask model in src/models/processing_task.py with status tracking"
Task: "Create Report model in src/models/report.py with processing_status field"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
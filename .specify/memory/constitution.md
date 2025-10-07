<!-- 
SYNC IMPACT REPORT:
Version change: N/A -> 1.0.0 (initial constitution for project)
Modified principles: N/A (initial creation)
Added sections: All principles and sections (new constitution)
Removed sections: N/A
Templates requiring updates: 
- ✅ .specify/templates/plan-template.md 
- ✅ .specify/templates/spec-template.md 
- ✅ .specify/templates/tasks-template.md 
- ⚠ .qwen/commands/*.toml (pending)
- ✅ README.md 
Follow-up TODOs: None
-->

# Система автоматизации реестра средств измерений (СИ) Constitution

## Core Principles

### Modern Python Stack
Использование современного Python стека (FastAPI, pandas, httpx). MUST use FastAPI for API framework, pandas for data processing, and httpx for HTTP requests. SHOULD follow Python 3.13+ standards and best practices.

### Comprehensive Test Coverage
Полное покрытие тестами (pytest). MUST implement comprehensive unit, integration, and end-to-end tests using pytest. All features require test coverage before deployment. Code coverage MUST be at least 90%.

### Containerization Through Docker
Контейнеризация через Docker. MUST containerize all services using Docker. Images MUST follow best practices for size optimization and security. SHOULD support multi-platform builds for deployment flexibility.

### Clean Architecture with Separation of Concerns
Чистая архитектура с разделением ответственности. MUST implement layered architecture with clear separation between business logic, data access, and presentation layers. Components MUST have single responsibility and low coupling. SHOULD follow SOLID principles.

### Error Handling and Data Validation
Обработка ошибок и валидация данных. MUST implement comprehensive error handling at all levels. Data MUST be validated at entry points with appropriate error responses. SHOULD use proper logging for debugging and monitoring.

### Asynchronous API Requests
Асинхронные запросы к API. MUST implement asynchronous operations when interacting with external services like Arshin registry API. SHOULD optimize for performance and handle rate limiting appropriately.

## Technology Stack Requirements

Modern Python development stack including FastAPI, pandas, httpx, pytest, and Docker. MUST adhere to semantic versioning for dependencies. SHOULD regularly update dependencies to maintain security.

## Development Workflow

All code changes MUST pass comprehensive testing before merging. Code reviews are REQUIRED for all PRs. MUST follow standard Python formatting (PEP 8) and documentation practices. SHOULD implement continuous integration and deployment pipelines.

## Governance

This constitution supersedes all other development practices. All team members MUST comply with these principles. Amendments REQUIRE documentation and approval from project leadership. All PRs and reviews MUST verify compliance with these principles.

**Version**: 1.0.0 | **Ratified**: 2025-10-07 | **Last Amended**: 2025-10-07
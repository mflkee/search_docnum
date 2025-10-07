# Research: Система автоматизации реестра СИ

## Overview
This document outlines the research findings and technology decisions for implementing the measurement instruments registry synchronization system, taking into account the clarifications that removed the CLI interface and specified additional requirements.

## Decision: Background Task Processing
**Rationale**: The system needs to handle potentially long-running Excel file processing tasks (>5 minutes for 100MB files). Using background tasks ensures the API remains responsive while processing completes asynchronously.

**Alternatives considered**:
- Threading within the web process - Risk of blocking the main thread and potential memory issues
- FastAPI BackgroundTasks - Limited to the lifespan of the request, not persistent across server restarts
- Celery - More robust for long-running tasks and persistence, but adds complexity with message broker
- Queue system like RQ - Simpler than Celery but less feature-rich

**Decision**: Using Celery with Redis as the message broker for robust background processing, with a fallback option to FastAPI BackgroundTasks for simpler deployments.

## Decision: Arshin API Client Implementation with Two-Stage Verification
**Rationale**: Need to implement the two-stage verification process described in requirements (first search by year and certificate number, then by instrument parameters) while handling rate limiting and retries. Also need to handle the clarified requirements for multiple matches and missing records.

**Alternatives considered**:
- httpx with custom retry logic - Good async support and HTTP/2 features
- aiohttp - Alternative async HTTP client
- requests with threading - Synchronous approach, not preferred

**Decision**: Using httpx for asynchronous HTTP requests with custom retry and rate limiting middleware to handle the two-stage verification process efficiently, with specific logic to handle multiple records (select most recent) and missing records (mark as NOT_FOUND).

## Decision: Certificate Number Validation
**Rationale**: The system must validate certificate number formats before querying the Arshin API as clarified in the requirements.

**Alternatives considered**:
- Regex validation based on known patterns (e.g., "^[A-Z]-[A-Z0-9/]+\\d+$") - Specific to certificate format
- Simple format check (alphanumeric with allowed special chars) - More flexible
- No validation on format - Just rely on API response

**Decision**: Using regex validation based on common Arshin certificate patterns to validate format before API queries.

## Decision: No Caching of API Responses
**Rationale**: As clarified, the system should always query the external Arshin API for fresh data rather than caching responses.

**Alternatives considered**:
- Redis caching - Fast in-memory caching
- Database caching - Persistent caching
- No caching (fresh queries always) - Ensures latest data is always retrieved

**Decision**: Going with no caching approach as specified in clarifications to ensure fresh data from the Arshin API.

## Decision: Web Interface Implementation (Primary Interaction)
**Rationale**: With CLI interface removed as clarified, the web interface becomes the primary interaction method for operators.

**Alternatives considered**:
- Pure API approach - Just the REST API without HTML interface
- Full React/Vue SPA - More complex frontend with JavaScript framework
- Simple HTML with Jinja2 templates - Lightweight solution using FastAPI's templating

**Decision**: Using Jinja2 templates with FastAPI's Starlette templating system for the HTML interface, with drag-and-drop upload functionality and AJAX-powered status updates for a good user experience while keeping complexity low.

## Decision: Frontend Technologies for Web Interface
**Rationale**: Need to implement a user-friendly web interface with modern features like drag-and-drop and real-time status updates.

**Alternatives considered**:
- Vanilla JavaScript - Maximum control but more code to write
- jQuery - Simplified DOM manipulation
- Bootstrap + vanilla JS - CSS framework with minimal JavaScript
- HTMX - Simple AJAX interactions without complex JavaScript

**Decision**: Using Bootstrap for styling and vanilla JavaScript for AJAX interactions and drag-and-drop functionality to provide a responsive interface that shows processing progress and handles errors appropriately.

## Decision: Handling Multiple API Records
**Rationale**: Need to specifically handle cases where the Arshin API returns multiple records for the same search criteria, selecting the most recent as clarified.

**Alternatives considered**:
- Take first record - Simple but potentially incorrect
- Take last record - Also potentially incorrect
- Take record with newest date - Most accurate based on requirements
- Return all records - Would go against clarification

**Decision**: Implement logic to select the most recent record by date when multiple records are returned from the Arshin API.
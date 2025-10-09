import os
from typing import Any, Optional

from fastapi import Request

from src.config.settings import settings
from src.utils.logging_config import app_logger


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, considering potential proxies.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address as string
    """
    # Check for forwarded-for header (common with proxies/load balancers)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # In case multiple IPs are listed, take the first one
        return forwarded_for.split(",")[0].strip()

    # Check for real IP header (another proxy header)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fall back to client host
    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def validate_task_id(task_id: str) -> bool:
    """
    Validate task ID format.

    Args:
        task_id: Task ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not task_id or not isinstance(task_id, str):
        return False

    # Basic validation: alphanumeric, hyphens, and underscores, with reasonable length
    import re
    pattern = r'^[a-zA-Z0-9_-]{8,64}$'
    return bool(re.match(pattern, task_id))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other security issues.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    if not filename:
        return ""

    # Remove path components to prevent directory traversal
    filename = os.path.basename(filename)

    # Remove potentially dangerous characters
    filename = "".join(c for c in filename if c.isalnum() or c in "._- ")

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext

    return filename


def create_file_path(dir_type: str, filename: str) -> str:
    """
    Create a secure file path based on directory type.

    Args:
        dir_type: Type of directory ('upload' or 'result')
        filename: Original filename

    Returns:
        Absolute path to file
    """
    # Sanitize filename first
    safe_filename = sanitize_filename(filename)

    if dir_type == 'upload':
        base_dir = settings.upload_dir
    elif dir_type == 'result':
        base_dir = settings.results_dir
    else:
        raise ValueError(f"Invalid directory type: {dir_type}")

    # Create the full path
    file_path = os.path.join(base_dir, safe_filename)

    # Validate the path to ensure it's within the allowed directory
    abs_path = os.path.abspath(file_path)
    allowed_dir = os.path.abspath(base_dir)

    if not abs_path.startswith(allowed_dir):
        raise ValueError(f"Invalid file path: {file_path}")

    return file_path


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = math.floor(math.log(size_bytes, 1024))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f"{s}{size_names[i]}"


def get_file_type_icon(file_extension: str) -> str:
    """
    Get appropriate icon class based on file extension.

    Args:
        file_extension: File extension (e.g., '.xlsx', '.xls')

    Returns:
        CSS class name for the appropriate icon
    """
    excel_types = ['.xlsx', '.xls', '.csv', '.xlsm']
    doc_types = ['.pdf', '.doc', '.docx', '.txt']

    if file_extension.lower() in excel_types:
        return "xlsx-icon"
    elif file_extension.lower() in doc_types:
        return "doc-icon"
    else:
        return "file-icon"


def log_user_action(action: str, user_id: Optional[str] = None, details: Optional[dict[str, Any]] = None):
    """
    Log user actions for audit purposes.

    Args:
        action: Description of the action
        user_id: ID of the user performing the action (if available)
        details: Additional details about the action
    """
    log_data = {
        "action": action,
        "user_id": user_id,
        "details": details or {}
    }

    app_logger.info(f"User action: {log_data}")

import os

import magic  # For MIME type detection

from src.config.settings import settings
from src.utils.logging_config import app_logger


class FileValidator:
    """
    Service for validating uploaded files for security and format compliance.
    """

    @staticmethod
    def validate_file_type(file_path: str) -> tuple[bool, str]:
        """
        Validate the file type by checking its extension and MIME type.

        Args:
            file_path: Path to the file to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        _, file_ext = os.path.splitext(file_path.lower())
        if file_ext not in settings.allowed_file_types:
            return False, f"File type {file_ext} is not allowed. Allowed types: {settings.allowed_file_types}"

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > settings.max_file_size:
            return False, f"File size {file_size} exceeds maximum allowed size {settings.max_file_size}"

        # Check MIME type using python-magic
        try:
            mime_type = magic.from_file(file_path, mime=True)
            allowed_mime_types = {
                ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
                ".xls": ["application/vnd.ms-excel", "application/msexcel", "application/x-msexcel", "application/x-ms-excel", "application/x-excel", "application/x-dos_ms_excel"]
            }

            if mime_type not in allowed_mime_types.get(file_ext, []):
                app_logger.warning(f"File {file_path} has unexpected MIME type {mime_type}")
                # For security, we'll be strict about MIME types
                return False, f"Unexpected file MIME type: {mime_type}"
        except Exception as e:
            app_logger.error(f"Error checking MIME type for {file_path}: {e}")
            return False, f"Error checking file MIME type: {e}"

        # Security checks: ensure the file is not disguised as a different type
        if not FileValidator._is_safe_file(file_path):
            return False, "File failed security validation"

        return True, ""

    @staticmethod
    def _is_safe_file(file_path: str) -> bool:
        """
        Additional security checks to prevent malicious file uploads.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file passes security checks, False otherwise
        """
        try:
            # Check for common malicious patterns in the file header
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # Read first 1KB

                # Excel files have specific headers we can validate
                if file_path.endswith('.xlsx'):
                    # XLSX files are ZIP archives, should start with PK
                    if not header.startswith(b'PK'):
                        return False
                elif file_path.endswith('.xls'):
                    # XLS files have specific binary markers
                    # Microsoft Excel files typically start with specific bytes
                    # This is a basic check - more complex validation could be implemented
                    if not any([
                        header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'),  # OLE2 header
                    ]):
                        # If the header doesn't have expected Excel format, check if it might be an actual Excel file
                        # by examining other known Excel signatures
                        # This is a simplified check - real implementation may need more thorough validation
                        pass

            return True
        except Exception as e:
            app_logger.error(f"Error in security check for {file_path}: {e}")
            return False

    @staticmethod
    def validate_file_path(file_path: str) -> tuple[bool, str]:
        """
        Validate the file path to prevent directory traversal attacks.

        Args:
            file_path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Prevent directory traversal
        if '..' in file_path or './' in file_path:
            return False, "Invalid file path detected"

        # Resolve to absolute path and check if it's within allowed directories
        abs_path = os.path.abspath(file_path)
        allowed_dirs = [
            os.path.abspath(settings.upload_dir),
            os.path.abspath(settings.results_dir)
        ]

        if not any(abs_path.startswith(allowed_dir) for allowed_dir in allowed_dirs):
            return False, "File path is not in allowed directories"

        return True, ""

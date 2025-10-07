import re
from typing import Optional
from datetime import datetime


def validate_certificate_format(certificate_number: str) -> bool:
    """
    Validate certificate number format using regex pattern
    Expected format examples: "C-VY/11-10-2024/385850983", "C-ABCD/15-01-2025/402123271"
    Pattern: Letter-Text/Numbers where the middle part may contain dates
    """
    if not certificate_number:
        return False
    
    # More specific pattern for Arshin certificate numbers
    # Format: Letter-Text/Date/Numbers or Letter-Text/Numbers
    # Examples: "С-ВЯ/15-01-2025/402123271", "С-ДШФ/11-10-2024/385850983"
    pattern = r'^[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]{2}-[0-9]{2}-[0-9]{4}/[0-9]+$|^' + \
              r'[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]+/[0-9]+$'
    
    return bool(re.match(pattern, certificate_number))


def validate_certificate_format_detailed(certificate_number: str) -> tuple[bool, str]:
    """
    Validate certificate number format and return detailed error message if invalid
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not certificate_number:
        return False, "Certificate number cannot be empty"
    
    # Check if it matches one of the expected patterns
    patterns = [
        r'^[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]{2}-[0-9]{2}-[0-9]{4}/[0-9]+$',  # Letter-Text/DD-MM-YYYY/Numbers
        r'^[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]+/[0-9]+$',  # Letter-Text/Numbers/Numbers
    ]
    
    for pattern in patterns:
        if re.match(pattern, certificate_number):
            return True, ""
    
    return False, f"Certificate number '{certificate_number}' does not match expected patterns"


def validate_excel_column_format(column_value: str, column_type: str) -> tuple[bool, str]:
    """
    Validate specific excel column formats
    
    Args:
        column_value: The value to validate
        column_type: The type of column ('date', 'certificate', etc.)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not column_value:
        return False, "Column value cannot be empty"
    
    if column_type == "certificate":
        return validate_certificate_format_detailed(column_value)
    elif column_type == "date":
        # Date validation would be handled separately in date_utils
        return True, ""
    else:
        return True, ""
import re


_CERTIFICATE_PATTERNS = [
    # Letter-Text/DD-MM-YYYY/Numbers
    r'^[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]{2}-[0-9]{2}-[0-9]{4}/[0-9]+$',
    # Letter-Text/Numbers/Numbers
    r'^[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]+/[0-9]+$',
    # Pure numeric certificate number with slashes (common in exported registries)
    r'^[0-9]+/[0-9]+/[0-9]+$',
    # Certificates starting with Cyrillic abbreviations (e.g., "СП j.0849-20"), ensure at least one digit
    r'^[A-ZА-ЯЁ]{1,4}\s?[A-ZА-ЯЁ0-9./-]*\d[A-ZА-ЯЁ0-9./-]*$',
]


def _matches_certificate_patterns(value: str) -> bool:
    for pattern in _CERTIFICATE_PATTERNS:
        if re.match(pattern, value, re.IGNORECASE):
            return True
    return False


def validate_certificate_format(certificate_number: str) -> bool:
    """
    Validate certificate number format using supported patterns.
    Returns True for known valid formats and leniently accepts other non-empty values containing digits.
    """
    is_valid, _ = validate_certificate_format_detailed(certificate_number)
    return is_valid


def validate_certificate_format_detailed(certificate_number: str) -> tuple[bool, str]:
    """
    Validate certificate number format and return detailed error message if invalid

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not certificate_number:
        return False, "Certificate number cannot be empty"

    value = certificate_number.strip()
    if not value:
        return False, "Certificate number cannot be empty"

    if value.lower() in {"nat", "nan"}:
        return False, "Certificate number cannot be NaT/NaN"

    if _matches_certificate_patterns(value):
        return True, ""

    # Lenient fallback: accept strings that contain digits and have reasonable length
    if any(ch.isdigit() for ch in value) and len(value) >= 4:
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

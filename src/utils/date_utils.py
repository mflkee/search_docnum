import re
from datetime import datetime
from typing import Optional


def parse_verification_date(date_str: str) -> Optional[datetime]:
    """
    Parse verification date from Excel file, handling multiple formats.

    Supported formats:
    - DD.MM.YYYY (e.g., 11.10.2024)
    - YYYY-MM-DD (e.g., 2024-10-11)
    - DD/MM/YYYY
    - MM/DD/YYYY

    Args:
        date_str: Date string from Excel file

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_str:
        return None

    # Handle pandas NaN values (converted to float('nan') then to string 'nan')
    if str(date_str).lower() in ['nan', 'none', '<na>', 'nat', '']:
        return None

    # Check if the string contains obvious non-date text like 'IP' followed by numbers
    # These are likely not date values but other data
    date_str = str(date_str).strip()
    if 'ip' in date_str.lower():
        return None

    # Define supported date formats
    date_formats = [
        "%d.%m.%Y",  # DD.MM.YYYY
        "%Y-%m-%d",  # YYYY-MM-DD
        "%d/%m/%Y",  # DD/MM/YYYY
        "%m/%d/%Y",  # MM/DD/YYYY
        "%d.%m.%y",  # DD.MM.YY (for 2-digit years if needed)
        "%Y/%m/%d",  # YYYY/MM/DD
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
    ]

    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date
        except ValueError:
            continue

    # If none of the standard formats work, try to extract date parts manually
    # Pattern for DD.MM.YYYY or DD/MM/YYYY
    match = re.match(r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})', date_str)
    if match:
        try:
            day, month, year = match.groups()
            parsed_date = datetime(int(year), int(month), int(day))
            return parsed_date
        except ValueError:
            pass

    # Pattern for YYYY-MM-DD
    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if match:
        try:
            year, month, day = match.groups()
            parsed_date = datetime(int(year), int(month), int(day))
            return parsed_date
        except ValueError:
            pass

    return None


def extract_year_from_date(date_str: str) -> Optional[int]:
    """
    Extract year from date string, handling multiple formats and pandas NaN values.

    Args:
        date_str: Date string from Excel file (column AE)

    Returns:
        Year as integer or None if parsing fails
    """
    # Handle pandas NaN and other null values early
    if not date_str:
        return None

    # Handle pandas NaN values (converted to float('nan') then to string 'nan')
    if str(date_str).lower() in ['nan', 'none', '<na>', 'nat', '']:
        return None

    parsed_date = parse_verification_date(date_str)
    if parsed_date:
        return parsed_date.year
    return None


def format_date_for_arshin_api(date_obj: datetime) -> str:
    """
    Format date for use in Arshin API calls.

    Args:
        date_obj: Datetime object to format

    Returns:
        Formatted date string for API (YYYY-MM-DD)
    """
    if not date_obj:
        return ""
    return date_obj.strftime("%Y-%m-%d")


def is_valid_date_range(start_date: datetime, end_date: datetime, max_range_years: int = 10) -> bool:
    """
    Check if the date range is within acceptable limits.

    Args:
        start_date: Start date
        end_date: End date
        max_range_years: Maximum allowed range in years

    Returns:
        True if range is valid, False otherwise
    """
    if not start_date or not end_date:
        return False

    # Calculate the difference in years
    year_diff = abs(end_date.year - start_date.year)
    return year_diff <= max_range_years

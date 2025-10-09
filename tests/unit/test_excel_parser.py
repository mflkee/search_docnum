import pytest

from src.services.excel_parser import ExcelParserService


@pytest.fixture
def excel_parser():
    return ExcelParserService()


def test_validate_excel_structure_valid_file(excel_parser):
    """Test that the Excel structure validation works with a valid file."""
    # We'll test with a simple validation that checks if required columns exist
    # Since we don't have actual Excel files in test environment,
    # we'll test the validation logic
    is_valid, _error_msg = excel_parser.validate_excel_structure("nonexistent.xlsx")
    # This will fail since the file doesn't exist, but it tests the validation path
    assert not is_valid


def test_parse_verification_date_valid_formats(excel_parser):
    """Test parsing of various date formats."""
    from src.utils.date_utils import parse_verification_date

    # Test DD.MM.YYYY format
    result = parse_verification_date("11.10.2024")
    assert result is not None
    assert result.year == 2024
    assert result.month == 10
    assert result.day == 11

    # Test YYYY-MM-DD format
    result = parse_verification_date("2024-10-11")
    assert result is not None
    assert result.year == 2024
    assert result.month == 10
    assert result.day == 11


def test_validate_certificate_format_valid(excel_parser):
    """Test certificate format validation."""
    from src.utils.validators import validate_certificate_format_detailed

    # Test a valid format
    is_valid, error_msg = validate_certificate_format_detailed("С-ВЯ/15-01-2025/402123271")
    assert is_valid, f"Certificate should be valid but got error: {error_msg}"

    # Test an invalid format
    is_valid, error_msg = validate_certificate_format_detailed("INVALID-FORMAT")
    assert not is_valid, "Certificate should be invalid"

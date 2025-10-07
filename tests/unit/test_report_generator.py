import pytest

from src.models.report import ProcessingStatus, Report
from src.services.report_generator import ReportGeneratorService


@pytest.fixture
def report_generator():
    return ReportGeneratorService()


def test_report_generator_initialization(report_generator):
    """Test that ReportGeneratorService initializes properly."""
    assert report_generator is not None
    assert len(report_generator.report_columns) > 0


def test_validate_report_data_empty_list(report_generator):
    """Test validation of empty report data."""
    is_valid, _error_msg = report_generator.validate_report_data([])
    assert is_valid, "Empty list should be valid"


def test_validate_report_data_valid_reports(report_generator):
    """Test validation of valid report data."""
    reports = [
        Report(
            arshin_id="12345",
            org_title="Test Org",
            mit_number="77090-19",
            mit_title="Test Device",
            mit_notation="TD-01",
            mi_number="123456789",
            verification_date="2024-01-15",
            valid_date="2025-01-15",
            result_docnum="C-TEST/01-15-2024/123456789",
            processing_status=ProcessingStatus.MATCHED,
            excel_source_row=1
        )
    ]

    is_valid, error_msg = report_generator.validate_report_data(reports)
    assert is_valid, f"Valid reports should pass validation, error: {error_msg}"

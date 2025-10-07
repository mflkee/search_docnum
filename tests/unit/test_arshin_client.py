import pytest
from src.services.arshin_client import ArshinClientService
from src.models.arshin_record import ArshinRegistryRecord


@pytest.fixture
async def arshin_client():
    client = ArshinClientService()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_arshin_client_initialization(arshin_client):
    """Test that ArshinClientService initializes properly."""
    assert arshin_client is not None
    assert arshin_client.base_url is not None


def test_convert_to_arshin_record_valid_data():
    """Test conversion from API response to ArshinRegistryRecord."""
    client = ArshinClientService()
    
    # Sample API response data
    api_record = {
        'vri_id': '12345',
        'org_title': 'Test Organization',
        'mit_number': '77090-19',
        'mit_title': 'Test Device',
        'mit_notation': 'TD-01',
        'mi_number': '123456789',
        'verification_date': '2024-01-15',
        'valid_date': '2025-01-15',
        'result_docnum': 'C-TEST/01-15-2024/123456789'
    }
    
    result = client._convert_to_arshin_record(api_record, is_stage1_result=False)
    
    assert isinstance(result, ArshinRegistryRecord)
    assert result.vri_id == '12345'
    assert result.org_title == 'Test Organization'
    assert result.mit_number == '77090-19'
    assert result.verification_date.year == 2024
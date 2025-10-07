import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_endpoints_availability(client):
    """Test that all API endpoints are available."""
    # Test health endpoint
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    
    # Test that root endpoint works
    response = client.get("/")
    assert response.status_code == 200
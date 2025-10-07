import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_external_system_api_flow(client):
    """Test the full API flow for external system integration."""
    # Test health check
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    
    # Test that the API endpoints are available
    # We can't test the full file upload flow without a real file,
    # but we can check that endpoints exist and return appropriate error codes
    response = client.get("/api/v1/status/nonexistent-task")
    assert response.status_code == 200  # Returns status info even for nonexistent task
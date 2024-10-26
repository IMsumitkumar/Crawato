import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import Mock, patch
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture
def mock_supabase(mocker):
    mock = Mock()
    mocker.patch('app.db.database.supabase', mock)
    return mock

@pytest.fixture
def auth_headers():
    access_token = create_access_token(data={"sub": "test@example.com"})
    return {"Authorization": f"Bearer {access_token}"}

def test_create_dynamic_endpoint(mock_supabase, auth_headers):
    mock_supabase.table().insert().execute.return_value.data = [{
        "id": "123",
        "user_id": "456",
        "endpoint_url": "test-endpoint",
        "configuration_id": "789",
        "data_schema": {"title": "string"},
        "transformations": {"title": "lambda x: x.upper()"}
    }]

    with patch('app.api.auth.get_current_user', return_value={"id": "456"}):
        response = client.post("/dynamic/create", json={
            "configuration_id": "789",
            "endpoint_url": "test-endpoint",
            "data_schema": {"title": "string"},
            "transformations": {"title": "lambda x: x.upper()"}
        },
        headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["endpoint_url"] == "test-endpoint"

@pytest.mark.asyncio
async def test_dynamic_endpoint(mock_supabase, mocker, auth_headers):
    mock_supabase.table().select().eq().single().execute.return_value.data = {
        "id": "123",
        "user_id": "456",
        "endpoint_url": "test-endpoint",
        "configuration_id": "789",
        "data_schema": {"title": "string"},
        "transformations": {"title": "lambda x: x.upper()"}
    }
    print(1)
    mock_supabase.table().select().eq().execute.return_value.data = [{
        "url": "https://supabase.com/pricing",
        "selectors": {"title": "h1"}
    }]

    print(2)
    
    mocker.patch('app.api.dynamic_endpoints.scrape_url', return_value={"data": {"title": "Test Page"}})
    print(3)
    mocker.patch('app.api.dynamic_endpoints.process_and_validate_data', return_value={"title": "TEST PAGE"})
    print(4)
    response = client.get("/dynamic/test-endpoint?value=1", headers=auth_headers)
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    assert response.status_code == 200
    assert response.json()["title"] == "TEST PAGE"

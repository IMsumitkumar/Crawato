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

def test_create_configuration(mock_supabase, auth_headers):
    mock_insert = mock_supabase.table.return_value.insert.return_value
    mock_insert.execute.return_value.data = [{
        "id": "123",
        "name": "Test Config",
        "url": "https://supabase.com/pricing",
        "selectors": {"title": "h1"},
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }]

    with patch('app.api.auth.get_current_user', return_value={"id": "123", "email": "test@example.com"}):
        response = client.post(
            "/configurations/configurations", 
            json={
                "name": "Test Config",
                "url": "https://supabase.com/pricing",
                "selectors": {"title": "h1"}
            },
            headers=auth_headers
        )

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    
    assert response.status_code == 200
    assert response.json()["name"] == "Test Config"
    assert response.json()["url"] == "https://supabase.com/pricing"

def test_get_configurations(mock_supabase, auth_headers):
    mock_supabase.table().select().eq().execute.return_value.data = [{
        "id": "123",
        "name": "Test Config",
        "url": "https://supabase.com/pricing",
        "selectors": {"title": "h1"},
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }]

    with patch('app.api.auth.get_current_user', return_value={"id": "123", "email": "test@example.com"}):
        response = client.get("/configurations/configurations", headers=auth_headers)
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test Config"

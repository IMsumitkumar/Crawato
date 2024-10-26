import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.api.auth import get_user, UserCreate
from unittest.mock import Mock
from app.db.database import supabase

client = TestClient(app)

@pytest.fixture
def mock_supabase(mocker):
    mock = Mock()
    mocker.patch('app.db.database.supabase', mock)
    
    return mock

def test_register(mock_supabase):
    mock_supabase.table().insert().execute.return_value.data = [{"id": "123", "email": "test@example.com", "full_name": "Test User"}]
    
    response = client.post("/auth/register", json={
        "email": "testb@example.com",
        "full_name": "Test User 2",
        "password": "testpassword"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "testb@example.com"
    assert response.json()["full_name"] == "Test User 2"

def test_login(mock_supabase):
    mock_supabase.table().select().eq().execute.return_value.data = [{"id": "123", "email": "test@example.com", "hashed_password": "$2b$12$1234567890123456789012"}]
    
    response = client.post("/auth/token", data={
        "username": "test@example.com",
        "password": "testpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_read_users_me(mock_supabase):
    mock_supabase.table().select().eq().execute.return_value.data = [{"id": "123", "email": "test@example.com", "full_name": "Test User"}]
    
    access_token = create_access_token(data={"sub": "test@example.com"})
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/auth/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

# @pytest.mark.database
def test_database_connection():
    try:
        # Attempt to fetch a single row from the users table
        result = supabase.table('users').select('*').limit(1).execute()
        
        # If we get here, the connection was successful
        assert True
    except Exception as e:
        pytest.fail(f"Database connection failed: {str(e)}")

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.scraping_service import scrape_url
from unittest.mock import AsyncMock, patch, Mock
from app.core.security import create_access_token



client = TestClient(app)



@pytest.fixture
def auth_headers():
    access_token = create_access_token(data={"sub": "test@example.com"})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_crawl4ai(mocker):
    mock = AsyncMock()
    mocker.patch('app.services.scraping_service.AsyncWebCrawler', return_value=mock)
    return mock

@pytest.mark.asyncio
async def test_scrape_url():
    url = "https://www.coinbase.com/explore"
    selectors = {
        "title": "h1",
        "description": "meta[name='description']::attr(content)",
        "first_paragraph": "p:first-of-type"
    }

    result = await scrape_url(url, selectors)
    print(result)

    assert "data" in result
    assert "metadata" in result
    assert "links" in result

@pytest.mark.asyncio
async def test_scrape_endpoint():
    access_token = create_access_token(data={"sub": "test@example.com"})
    print(access_token)
    with patch('app.api.auth.get_current_user', return_value={"id": "123"}):

        url = "https://www.coinbase.com/explore"
        selectors = {
            "title": "h1",
            "description": "meta[name='description']::attr(content)",
            "first_paragraph": "p:first-of-type"
        }
        response = client.post("/scraping/scrape", json={
                "url": url,
                "selectors": selectors
            }, headers= {"Authorization": f"Bearer {access_token}"}
        )
    
    assert response.status_code == 200


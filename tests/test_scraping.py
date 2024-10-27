import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.scraping_service import scrape_url, recommend_crawler
from app.services.crawler_factory import CrawlerFactory
from app.api.configurations import CrawlerType, ScrapingConfiguration, WaitCondition
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
async def test_basic_scrape_url(mock_crawl4ai):
    url = "https://www.coinbase.com/explore"
    config = {
        "crawler_type": CrawlerType.BASIC,
        "selectors": ["cleaned_html", "media", "links", "screenshot", "markdown", "metadata"]
    }

    mock_crawl4ai.arun.return_value.extracted_content = {"title": "Test Title", "content": "Test Content"}
    mock_crawl4ai.arun.return_value.status_code = 200

    print("config", config)
    result = await scrape_url(url, config)

    assert "data" in result

@pytest.mark.asyncio
async def test_llm_extraction_scrape_url(mock_crawl4ai):
    url = "https://openai.com/api/pricing/"
    extraction_instructions = (
        "From the crawled content, extract all mentioned model names along with their "
        "fees for input and output tokens. Make sure not to miss anything in the entire content. "
        "One extracted model JSON format should look like this: "
        '{ "model_name": "GPT-4", "input_fee": "US$10.00 / 1M tokens", "output_fee": "US$30.00 / 1M tokens" }'
    )
    config = {
        "crawler_type": CrawlerType.LLM_EXTRACTION,
        "extraction_instructions": extraction_instructions
    }

    mock_crawl4ai.arun.return_value.extracted_content = {"content": "Extracted main content"}
    mock_crawl4ai.arun.return_value.status_code = 200

    result = await scrape_url(url, config)

    assert "data" in result

@pytest.mark.asyncio
async def test_js_css_extraction_scrape_url(mock_crawl4ai):
    url = "https://www.coinbase.com/explore"
    js_code = """
    window.scrollTo(0, document.body.scrollHeight);
    new Promise(resolve => setTimeout(resolve, 2000));  // Wait for 2 seconds
    """

    wait_for = """
    () => {
        const articles = document.querySelectorAll('article.tease-card');
        return articles.length > 10;
    }
    """
    config = {
        "crawler_type": CrawlerType.JS_CSS_EXTRACTION,
        "css_selectors": {
            "name": "Coinbase Crypto Prices",
            "baseSelector": ".cds-tableRow-t45thuk",
            "fields": {
                "crypto": {
                    "css_selectors": ["td:nth-child(1) h2", "td.crypto-name"],
                    "type": "text"
                },
                "symbol": {
                    "css_selectors": ["td:nth-child(1) p"],
                    "type": "text"
                },
                "price": {
                    "css_selectors": ["td:nth-child(2)"],
                    "type": "text"
                }
            }
        },
        "javascript_code": js_code,
        "wait_conditions": wait_for
    }

    mock_crawl4ai.arun.return_value.extracted_content = {"field_0": "Title", "field_1": "Content"}
    mock_crawl4ai.arun.return_value.status_code = 200

    result = await scrape_url(url, config)

    assert "data" in result


@pytest.mark.asyncio
async def test_scrape_endpoint_basic(auth_headers):
    with patch('app.api.auth.get_current_user', return_value={"id": "123"}):
        with patch('app.services.scraping_service.scrape_url') as mock_scrape:
            mock_scrape.return_value = {"data": {}, "metadata": {"status": 200}}
            print(1)
            response = client.post("/scrape", json={
                "url": "https://www.coinbase.com/explore",
                "crawler_type": "basic",
                "selectors": ["cleaned_html", "media", "links", "screenshot", "markdown", "metadata"]
            }, headers=auth_headers)
            print(2)

    

@pytest.mark.asyncio
async def test_scrape_endpoint_llm(auth_headers):
    with patch('app.api.auth.get_current_user', return_value={"id": "123"}):
        with patch('app.services.scraping_service.scrape_url') as mock_scrape:
            mock_scrape.return_value = {"data": {"content": "Extracted content"}, "metadata": {"status": 200}}
            
            response = client.post("/scrape", json={
                "url": "https://www.coinbase.com/explore",
                "crawler_type": "llm_extraction",
                "extraction_instructions": "Extract main content"
            }, headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["result"]["data"]["content"] == "Extracted content"

@pytest.mark.asyncio
async def test_scrape_endpoint_js_css(auth_headers):
    with patch('app.api.auth.get_current_user', return_value={"id": "123"}):
        with patch('app.services.scraping_service.scrape_url') as mock_scrape:
            mock_scrape.return_value = {"data": {"field_0": "Title"}, "metadata": {"status": 200, "js_executed": True}}
            
            response = client.post("/scrape", json={
                "url": "https://www.coinbase.com/explore",
                "crawler_type": "js_css_extraction",
                "css_selectors": [".title"],
                "javascript_code": "window.scrollTo(0, document.body.scrollHeight);"
            }, headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["result"]["data"]["field_0"] == "Title"
    assert response.json()["result"]["metadata"]["js_executed"] == True

def test_recommend_crawler():
    result = recommend_crawler("dynamic", "structured")
    assert result["recommended_crawler"] == CrawlerType.JS_CSS_EXTRACTION

    result = recommend_crawler("static", "unstructured")
    assert result["recommended_crawler"] == CrawlerType.LLM_EXTRACTION

    result = recommend_crawler("static", "structured")
    assert result["recommended_crawler"] == CrawlerType.BASIC

@pytest.mark.asyncio
async def test_recommend_crawler_endpoint(auth_headers):
    with patch('app.api.auth.get_current_user', return_value={"id": "123"}):
        response = client.post("/scraping/recommend-crawler", json={
            "website_type": "dynamic",
            "desired_data": "structured"
        }, headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["recommended_crawler"] == CrawlerType.JS_CSS_EXTRACTION

@pytest.mark.asyncio
async def test_scrape_url_error_handling(mock_crawl4ai):
    url = "https://www.coinbase.com/explore"
    config = {
        "crawler_type": CrawlerType.BASIC,
        "selectors": ['media', 'links', 'screenshot', 'markdown', 'metadata']
    }

    mock_crawl4ai.arun.side_effect = Exception("Scraping failed")

    result = await scrape_url(url, config)

    assert "error" in result
    assert "Scraping failed" in result["error"]

@pytest.mark.asyncio
async def test_scrape_endpoint_error_handling(auth_headers):
    response = client.post("/scraping/scrape", json={
        "url": "https://www.coinbase.com/explore",
        "crawler_type": "basic",
        "selectors": ['media']
    }, headers=auth_headers)

    print(response.json())
    

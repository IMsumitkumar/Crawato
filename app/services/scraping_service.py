from typing import Dict, List, Any
from crawl4ai import AsyncWebCrawler
from urllib.parse import urlparse
import json
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import asyncio

def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def clean_data(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [clean_data(item) for item in data if item is not None]
    elif isinstance(data, str):
        return data.strip()
    else:
        return data

async def scrape_url(url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
    if not validate_url(url):
        raise ValueError("Invalid URL provided")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        try:
            schema = {
                "name": "Basic Extraction",
                "baseSelector": "html",
                "fields": [
                    {
                        "name": key,
                        "selector": value,
                        "type": "text"
                    } for key, value in selectors.items()
                ]
            }
            extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)
            result = await crawler.arun(url=url, extraction_strategy=extraction_strategy)

            cleaned_result = clean_data(result.extracted_content)
            
            metadata = {
                "url": url,
                "status": result.status_code,
            }
            
            return {
                "data": cleaned_result,
                "metadata": metadata,
                # "links": result.links
            }
        except Exception as e:
            raise Exception(f"Scraping failed: {str(e)}")

def format_output(scrape_result: Dict[str, Any]) -> str:
    return json.dumps(scrape_result, indent=2)

async def scrape_multiple_urls(urls: List[str], selectors: Dict[str, str]) -> List[Dict[str, Any]]:
    async with AsyncWebCrawler(verbose=True) as crawler:
        tasks = [scrape_single_url(crawler, url, selectors) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

async def scrape_single_url(crawler: AsyncWebCrawler, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
    if not validate_url(url):
        raise ValueError(f"Invalid URL provided: {url}")

    try:
        result = await crawler.arun(url=url, css_selector=selectors)
        cleaned_result = clean_data(result.extracted_content)
        
        return {
            "data": cleaned_result,
            "metadata": {
                "url": url,
                "timestamp": result.timestamp,
                "status": result.status_code
            },
            "links": result.links
        }
    except Exception as e:
        return {"error": f"Scraping failed for {url}: {str(e)}"}

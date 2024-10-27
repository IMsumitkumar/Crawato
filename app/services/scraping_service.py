from typing import Dict, Any
import json
import asyncio
import os
import time
from app.models.scraping import CrawlerType, ScrapingConfiguration
from app.services.crawler_factory import get_crawler
from app.utils.validation import validate_url
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to store basic monitoring metrics
monitoring_metrics = {
    "total_requests": 0,
    "crawler_usage": {
        CrawlerType.BASIC: 0,
        CrawlerType.LLM_EXTRACTION: 0,
        CrawlerType.JS_CSS_EXTRACTION: 0
    },
    "average_execution_time": {
        CrawlerType.BASIC: 0,
        CrawlerType.LLM_EXTRACTION: 0,
        CrawlerType.JS_CSS_EXTRACTION: 0
    },
    "error_count": 0
}

def update_metrics(crawler_type: CrawlerType, execution_time: float, error: bool = False):
    monitoring_metrics["total_requests"] += 1
    monitoring_metrics["crawler_usage"][crawler_type] += 1
    
    # Update average execution time
    current_avg = monitoring_metrics["average_execution_time"][crawler_type]
    current_count = monitoring_metrics["crawler_usage"][crawler_type]
    new_avg = (current_avg * (current_count - 1) + execution_time) / current_count
    monitoring_metrics["average_execution_time"][crawler_type] = new_avg
    
    if error:
        monitoring_metrics["error_count"] += 1

def clean_data(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [clean_data(item) for item in data if item is not None]
    elif isinstance(data, str):
        return data.strip()
    else:
        return data
    

async def scrape_url(url: str, config: Dict[str, Any]) -> Dict[str, Any]:
    if not validate_url(url):
        raise ValueError("Invalid URL provided")
    
    start_time = time.time()
    crawler_type = config.get("crawler_type", CrawlerType.BASIC)

    print(crawler_type)
    
    try:
        logger.info(f"Starting scraping operation for URL: {url} with crawler type: {crawler_type}")

        print("Starting")
        
        # Convert the config dict to a ScrapingConfiguration object
        scraping_config = ScrapingConfiguration(
            name="Temporary Configuration",
            url=url,
            crawler_type=crawler_type,
            selectors=config.get("selectors"),
            extraction_instructions=config.get("extraction_instructions"),
            css_selectors=config.get("css_selectors"),
            javascript_code=config.get("javascript_code"),
            wait_conditions=config.get("wait_conditions")
        )

        print("Scraping config", scraping_config)

        # Use the crawler factory to get the appropriate crawler instance
        crawler, strategy_config = await get_crawler(scraping_config)

        print("Strategy config", strategy_config)

        
        async with crawler as crawl:
            if strategy_config and crawler_type != CrawlerType.BASIC:
                params = {
                    "url": url,
                    "bypass_cache": True,
                    **{k: v for k, v in {
                        "extraction_strategy": strategy_config.get("extraction_strategy"),
                        "js_code": strategy_config.get("javascript_code"),
                        "wait_for": strategy_config.get("wait_conditions")
                    }.items() if v is not None}
                }
                print("Params", params)
                result = await crawl.arun(**params)
            else:
                print("Basic crawler")
                result = await crawl.arun(url=url, bypass_cache=True)



        # Process the result based on the crawler type
        if result.status_code != 200:
            error_message = result.error_message if hasattr(result, 'error_message') else f"HTTP Error: {result.status_code}"
            return {
                "error": error_message,
                "metadata": {
                    "url": url,
                    "status": result.status_code,
                    "crawler_type": scraping_config.crawler_type
                }
            }

        if not result.extracted_content:
            return {
                "error": "No content extracted. The extraction might have failed.",
                "metadata": {
                    "url": url,
                    "status": result.status_code,
                    "crawler_type": scraping_config.crawler_type
                }
            }

        if scraping_config.crawler_type == CrawlerType.BASIC:
            # For backward compatibility with basic scraping
            final_result = {
                "status": True,
                "status": result.status_code,
                "selectors": {
                    selector: getattr(result, selector, None)
                    for selector in strategy_config.get("basic_res_selectors", [])
                    if hasattr(result, selector)
                }
            }
        else:
            # For LLM and JS/CSS extraction
            final_result = {
                "status": True,
                "data": result.markdown,
                "status": result.status_code,
                "selectors": {
                    "url": url,
                    "status": result.status_code,
                    "crawler_type": scraping_config.crawler_type,
                    "js_executed": bool(scraping_config.javascript_code),
                    "wait_conditions_applied": bool(scraping_config.wait_conditions)
                }
            }



        execution_time = time.time() - start_time
        update_metrics(crawler_type, execution_time)
        logger.info(f"Scraping completed for URL: {url}. Execution time: {execution_time:.2f} seconds")
        return final_result

    except asyncio.TimeoutError:
        error_message = "Timeout occurred while waiting for content to load"
        logger.error(f"Scraping failed for URL: {url}. Error: {error_message}")
        update_metrics(crawler_type, time.time() - start_time, error=True)
        return {
            "error": error_message,
            "metadata": {
                "url": url,
                "crawler_type": crawler_type
            }
        }
    except ValueError as ve:
        logger.error(f"Scraping failed for URL: {url}. Error: {str(ve)}")
        update_metrics(crawler_type, time.time() - start_time, error=True)
        return {
            "error": str(ve),
            "metadata": {
                "url": url,
                "crawler_type": crawler_type
            }
        }
    except Exception as e:
        logger.error(f"Scraping failed for URL: {url}. Error: {str(e)}")
        update_metrics(crawler_type, time.time() - start_time, error=True)
        return {
            "error": f"Scraping failed: {str(e)}",
            "metadata": {
                "url": url,
                "crawler_type": crawler_type
            }
        }

def format_output(scrape_result: Dict[str, Any]) -> str:
    return json.dumps(scrape_result, indent=2)


def recommend_crawler(website_type: str, desired_data: str) -> Dict[str, Any]:
    website_type = website_type.lower()
    desired_data = desired_data.lower()

    if "dynamic" in website_type or "javascript" in website_type or "spa" in website_type:
        return {
            "recommended_crawler": CrawlerType.JS_CSS_EXTRACTION,
            "explanation": "For dynamic websites or Single Page Applications (SPAs), the JS/CSS Extraction crawler is recommended. It can handle JavaScript-rendered content and complex DOM structures."
        }
    elif "unstructured" in desired_data or "text" in desired_data or "article" in desired_data:
        return {
            "recommended_crawler": CrawlerType.LLM_EXTRACTION,
            "explanation": "For extracting unstructured data or processing text content like articles, the LLM Extraction crawler is recommended. It can understand context and extract relevant information from complex text."
        }
    else:
        return {
            "recommended_crawler": CrawlerType.BASIC,
            "explanation": "For simple, static websites with structured data, the Basic crawler is recommended. It's efficient for extracting data from predictable HTML structures."
        }

# Add a new function to get monitoring metrics
def get_monitoring_metrics():
    return monitoring_metrics

from typing import Dict, Any
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
from app.models.scraping import CrawlerType, ScrapingConfiguration
import os

class CrawlerFactory:
    @staticmethod
    async def create_crawler(config: ScrapingConfiguration) -> AsyncWebCrawler:
        crawler = AsyncWebCrawler(verbose=True)

        if config.crawler_type == CrawlerType.BASIC:
            print("Creating basic crawler")
            return await CrawlerFactory._create_basic_crawler(crawler, config)
        elif config.crawler_type == CrawlerType.LLM_EXTRACTION:
            print("Creating llm extraction crawler")
            return await CrawlerFactory._create_llm_extraction_crawler(crawler, config)
        elif config.crawler_type == CrawlerType.JS_CSS_EXTRACTION:
            print("Creating js css extraction crawler")
            return await CrawlerFactory._create_js_css_extraction_crawler(crawler, config)
        else:
            raise ValueError(f"Unsupported crawler type: {config.crawler_type}")

    @staticmethod
    async def _create_basic_crawler(crawler: AsyncWebCrawler, config: ScrapingConfiguration) -> AsyncWebCrawler:

        config_dict = config.model_dump()

        return crawler, {
            "basic_res_selectors": config_dict.get("selectors")
        }

    @staticmethod
    async def _create_llm_extraction_crawler(crawler: AsyncWebCrawler, config: ScrapingConfiguration) -> AsyncWebCrawler:
        if not config.extraction_instructions:
            raise ValueError("Extraction instructions are required for LLM extraction")


        print("Creating llm extraction crawler . . . . . . .  . . . .  . . .  . . .")
        extraction_strategy = LLMExtractionStrategy(
            provider="openai/gpt-4o",  # You might want to make this configurable
            api_token="",  # Using OPEN_API_KEY from .env file
            instruction=config.extraction_instructions,
            extraction_type="text"  # You might want to make this configurable
        )
        # crawler.extraction_strategy = extraction_strategy
        return crawler, {
            "extraction_strategy": extraction_strategy
        }

    @staticmethod
    async def _create_js_css_extraction_crawler(crawler: AsyncWebCrawler, config: ScrapingConfiguration) -> AsyncWebCrawler:
        config_dict = config.model_dump()

        if not config_dict.get("css_selectors") and not config_dict.get("javascript_code"):
            raise ValueError("Either CSS selectors or JavaScript code is required for JS/CSS extraction")

        if config_dict.get("css_selectors"):
            css_selectors = config_dict.get("css_selectors")
            schema = {
                "name": css_selectors.get("name", "JS/CSS Extraction"),
                "baseSelector": css_selectors.get("baseSelector", "html"),
                "fields": [
                    {
                        "name": field_name,
                        "selectors": selectors if isinstance(selectors, list) else [selectors],
                        "type": field_info.get("type", "text")
                    }
                    for field_name, field_info in css_selectors.get("fields", {}).items()
                    for selectors in (field_info.get("selector"),)
                ]
            }
            extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)
        else:
            extraction_strategy = None

        return crawler, {
            "extraction_strategy": extraction_strategy,
            "javascript_code": config_dict.get("javascript_code"),
            "wait_conditions": config_dict.get("wait_conditions")
        }


async def get_crawler(config: ScrapingConfiguration) -> AsyncWebCrawler:
    return await CrawlerFactory.create_crawler(config)

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict
from enum import Enum

class CrawlerType(str, Enum):
    BASIC = "basic"
    LLM_EXTRACTION = "llm_extraction"
    JS_CSS_EXTRACTION = "js_css_extraction"

class WaitCondition(BaseModel):
    selector: str = Field(..., description="CSS selector to wait for")
    timeout: int = Field(default=30, ge=1, le=300, description="Maximum time to wait in seconds")

class ScrapingConfiguration(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the scraping configuration")
    description: Optional[str] = Field(None, max_length=500, description="Description of the scraping configuration")
    url: HttpUrl = Field(..., description="URL of the website to scrape")
    crawler_type: CrawlerType = Field(default=CrawlerType.BASIC, description="Type of crawler to use")
    selectors: Optional[List[str]] = Field(None, description="Selectors for the crawler")
    extraction_instructions: Optional[str] = Field(None, max_length=1000, description="Instructions for LLM-based extraction")
    css_selectors: Optional[Dict] = Field(None, description="List of CSS selectors for JS/CSS-based extraction")
    javascript_code: Optional[str] = Field(None, description="JavaScript code for dynamic content loading")
    wait_conditions: Optional[str] = Field(None,  description="Wait conditions for ensuring content is loaded")
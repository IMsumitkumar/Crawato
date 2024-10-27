from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, Optional, List
from app.services.scraping_service import scrape_url, format_output, recommend_crawler, get_monitoring_metrics
from app.api.auth import get_current_user
from app.models.scraping import CrawlerType, WaitCondition
import json

router = APIRouter()

class ScrapeRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL of the website to scrape")
    crawler_type: CrawlerType = Field(default=CrawlerType.BASIC, description="Type of crawler to use")
    selectors: Optional[Dict[str, str]] = Field(None, description="CSS selectors for basic scraping")
    extraction_instructions: Optional[str] = Field(None, description="Instructions for LLM-based extraction")
    model: Optional[str] = Field("gpt-3.5-turbo", description="LLM model to use for extraction")
    css_selectors: Optional[List[str]] = Field(None, description="List of CSS selectors for JS/CSS-based extraction")
    javascript_code: Optional[str] = Field(None, description="JavaScript code for dynamic content loading")
    wait_conditions: Optional[List[WaitCondition]] = Field(None, description="List of wait conditions for ensuring content is loaded")

    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com",
                "crawler_type": "js_css_extraction",
                "css_selectors": [".product-title", ".product-price"],
                "javascript_code": "window.scrollTo(0, document.body.scrollHeight);",
                "wait_conditions": [
                    {"selector": ".product-grid", "timeout": 60}
                ]
            }
        }

class ScrapeResponse(BaseModel):
    result: Dict[str, Any]

class CrawlerRecommendationRequest(BaseModel):
    website_type: str = Field(..., description="Type of website (e.g., dynamic, static, SPA)")
    desired_data: str = Field(..., description="Type of data to be extracted (e.g., structured, unstructured, text)")

class CrawlerRecommendationResponse(BaseModel):
    recommended_crawler: CrawlerType
    explanation: str

class MonitoringMetrics(BaseModel):
    total_requests: int
    crawler_usage: Dict[CrawlerType, int]
    average_execution_time: Dict[CrawlerType, float]
    error_count: int

@router.post("/scrape", response_model=ScrapeResponse, summary="Scrape a website", description="Scrape a website using the specified crawler type and configuration")
async def scrape(request: ScrapeRequest, current_user: Dict = Depends(get_current_user)):
    try:
        # Validate input based on crawler type
        if request.crawler_type == CrawlerType.BASIC and not request.selectors:
            raise ValueError("Selectors are required for basic scraping")
        elif request.crawler_type == CrawlerType.LLM_EXTRACTION and not request.extraction_instructions:
            raise ValueError("Extraction instructions are required for LLM extraction")
        elif request.crawler_type == CrawlerType.JS_CSS_EXTRACTION and not request.css_selectors:
            raise ValueError("CSS selectors are required for JS/CSS extraction")

        # Prepare configuration for scraping service
        config = {
            "crawler_type": request.crawler_type,
            "selectors": request.selectors,
            "extraction_instructions": request.extraction_instructions,
            "model": request.model,
            "css_selectors": request.css_selectors,
            "javascript_code": request.javascript_code,
            "wait_conditions": [wc.model_dump() for wc in request.wait_conditions] if request.wait_conditions else None
        }

        # Call scraping service
        result = await scrape_url(str(request.url), config)
        # Format and return the result
        formatted_result = format_output(result)
        return ScrapeResponse(result=json.loads(formatted_result))

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except NotImplementedError as nie:
        raise HTTPException(status_code=501, detail=str(nie))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@router.post("/recommend-crawler", response_model=CrawlerRecommendationResponse, summary="Get crawler recommendation", description="Get a recommendation for the best crawler type based on the website type and desired data")
async def get_crawler_recommendation(request: CrawlerRecommendationRequest, current_user: Dict = Depends(get_current_user)):
    try:
        recommendation = recommend_crawler(request.website_type, request.desired_data)
        return CrawlerRecommendationResponse(**recommendation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendation: {str(e)}")

@router.get("/metrics", response_model=MonitoringMetrics, summary="Get monitoring metrics", description="Retrieve monitoring metrics for crawler usage and performance")
async def get_metrics(current_user: Dict = Depends(get_current_user)):
    try:
        metrics = get_monitoring_metrics()
        return MonitoringMetrics(**metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve monitoring metrics: {str(e)}")

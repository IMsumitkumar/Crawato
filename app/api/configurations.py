from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Dict, Any, List, Optional
from app.db.database import (
    create_crawl_configuration,
    get_crawl_configurations,
    supabase,
)
from app.api.auth import get_current_user
from app.utils.validation import validate_url
from app.services.scraping_service import scrape_url
from app.models.scraping import CrawlerType, WaitCondition, ScrapingConfiguration
import time
from enum import Enum

router = APIRouter()


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
    extraction_instructions: Optional[str] = Field(None, max_length=1000, description="Instructions for LLM-based extraction")
    css_selectors: Optional[List[str]] = Field(None, description="List of CSS selectors for JS/CSS-based extraction")
    javascript_code: Optional[str] = Field(None, max_length=5000, description="JavaScript code for dynamic content loading")
    wait_conditions: Optional[List[WaitCondition]] = Field(None, description="List of wait conditions for ensuring content is loaded")

    @validator('extraction_instructions')
    def validate_extraction_instructions(cls, v, values):
        if values.get('crawler_type') == CrawlerType.LLM_EXTRACTION and not v:
            raise ValueError("Extraction instructions are required for LLM extraction")
        return v

    @validator('css_selectors')
    def validate_css_selectors(cls, v, values):
        if values.get('crawler_type') == CrawlerType.JS_CSS_EXTRACTION and not v:
            raise ValueError("CSS selectors are required for JS/CSS extraction")
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "Example Scraper",
                "description": "Scrapes product information from an e-commerce site",
                "url": "https://example.com/products",
                "crawler_type": "js_css_extraction",
                "css_selectors": [".product-title", ".product-price"],
                "javascript_code": "window.scrollTo(0, document.body.scrollHeight);",
                "wait_conditions": [
                    {"selector": ".product-grid", "timeout": 60}
                ]
            }
        }

class CrawlConfigurationCreate(BaseModel):
    name: str
    url: HttpUrl
    selectors: Dict[str, str]

class CrawlConfigurationUpdate(BaseModel):
    name: Optional[str] = Field(default=None)
    url: Optional[HttpUrl] = Field(default=None)
    selectors: Optional[Dict[str, str]] = Field(default=None)

class CrawlConfigurationResponse(BaseModel):
    id: str
    name: str
    url: HttpUrl
    selectors: Dict[str, str]
    created_at: str
    updated_at: str

@router.post("/configurations", response_model=CrawlConfigurationResponse)
async def create_configuration(
    config: CrawlConfigurationCreate,
    current_user: Dict = Depends(get_current_user)
):
    if not validate_url(str(config.url)):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    try:
        new_config = create_crawl_configuration(
            user_id=current_user.id,
            name=config.name,
            url=str(config.url),
            selectors=config.selectors
        )
        print("OKOKOKOKOK")
        if new_config.data and len(new_config.data) > 0:
            return CrawlConfigurationResponse(**new_config.data[0])
        else:
            raise HTTPException(status_code=500, detail="Failed to create configuration: No data returned")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create configuration: {str(e)}")

@router.get("/configurations", response_model=List[CrawlConfigurationResponse])
async def get_configurations(current_user: Dict = Depends(get_current_user)):
    try:
        configs = get_crawl_configurations(user_id=current_user.id)
        return [CrawlConfigurationResponse(**config) for config in configs.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve configurations: {str(e)}")

@router.put("/configurations/{config_id}", response_model=CrawlConfigurationResponse)
async def update_configuration(
    config_id: str,
    config_update: CrawlConfigurationUpdate,
    current_user: Dict = Depends(get_current_user)
):
    try:
        existing_config = supabase.table("crawl_configurations").select("*").eq("id", config_id).eq("user_id", current_user.id).single().execute()
        if not existing_config.data:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        update_data = config_update.model_dump(exclude_unset=True)
        if "url" in update_data and not validate_url(str(update_data["url"])):
            raise HTTPException(status_code=400, detail="Invalid URL")
        
        updated_config = supabase.table("crawl_configurations").update(update_data).eq("id", config_id).execute()
        return CrawlConfigurationResponse(**updated_config.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

@router.delete("/configurations/{config_id}", status_code=204)
async def delete_configuration(config_id: str, current_user: Dict = Depends(get_current_user)):
    try:
        existing_config = supabase.table("crawl_configurations").select("*").eq("id", config_id).eq("user_id", current_user.id).single().execute()
        if not existing_config.data:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        supabase.table("crawl_configurations").delete().eq("id", config_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration: {str(e)}")

@router.post("/configurations/{config_id}/test", response_model=Dict[str, Any])
async def test_configuration(config_id: str, current_user: Dict = Depends(get_current_user)):
    try:
        config = supabase.table("crawl_configurations").select("*").eq("id", config_id).eq("user_id", current_user.id).single().execute()
        if not config.data:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        start_time = time.time()
        result = scrape_url(config.data["url"], config.data["selectors"])
        end_time = time.time()
        
        execution_time = end_time - start_time
        supabase.table("performance_metrics").insert({
            "configuration_id": config_id,
            "execution_time": execution_time,
            "memory_usage": None  # You might want to implement memory usage tracking
        }).execute()
        
        return {
            "result": result,
            "execution_time": execution_time
        }
    except Exception as e:
        supabase.table("error_logs").insert({
            "configuration_id": config_id,
            "error_message": str(e),
            "stack_trace": None  # You might want to implement stack trace capturing
        }).execute()
        raise HTTPException(status_code=500, detail=f"Configuration test failed: {str(e)}")

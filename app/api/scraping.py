from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
from app.services.scraping_service import scrape_url, format_output
from app.api.auth import get_current_user
import json

router = APIRouter()

class ScrapeRequest(BaseModel):
    url: HttpUrl
    selectors: Dict[str, str]

class ScrapeResponse(BaseModel):
    result: Dict[str, Any]

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest, current_user: Dict = Depends(get_current_user)):
    try:

        print(1)
        result = await scrape_url(str(request.url), request.selectors)
        formatted_result = format_output(result)
        return ScrapeResponse(result=json.loads(formatted_result))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

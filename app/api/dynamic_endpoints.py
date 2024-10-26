from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, Optional
from app.db.database import (
    create_custom_endpoint, get_custom_endpoint, get_crawl_configurations,
    get_cache, set_cache, create_performance_metric, create_error_log,
    get_recent_performance_metrics, get_recent_error_logs
)
from app.api.auth import get_current_user
from app.services.scraping_service import scrape_url
from app.services.data_processing import process_and_validate_data
from app.core.config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address
import time
from datetime import datetime, timedelta

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class CustomEndpointCreate(BaseModel):
    configuration_id: str
    endpoint_url: str
    data_schema: Dict[str, Any]  # Changed from 'schema' to 'data_schema'
    transformations: Dict[str, str]

class CustomEndpointResponse(BaseModel):
    id: str
    user_id: str
    endpoint_url: str
    configuration_id: str
    data_schema: Dict[str, Any]  # Changed from 'schema' to 'data_schema'
    transformations: Dict[str, str]

@router.post("/create", response_model=CustomEndpointResponse)
async def create_dynamic_endpoint(
    endpoint: CustomEndpointCreate,
    current_user: Dict = Depends(get_current_user)
):
    try:
        new_endpoint = create_custom_endpoint(
            user_id=current_user.id,
            endpoint_url=endpoint.endpoint_url,
            configuration_id=endpoint.configuration_id,
            schema=endpoint.data_schema,
            transformations=endpoint.transformations
        )
        return CustomEndpointResponse(**new_endpoint.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create custom endpoint: {str(e)}")

@router.get("/{endpoint_url}")
@limiter.limit("10/minute")
async def dynamic_endpoint(endpoint_url: str, request: Request):
    print(11)
    try:
        endpoint = get_custom_endpoint(endpoint_url)
        print(endpoint.data)
        if not endpoint.data:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        config = get_crawl_configurations(endpoint.data.get("user_id"))
        if not config.data:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Implement caching
        
        cache_key = f"{endpoint_url}:{request.query_params}"
        print(cache_key)
        cached_result = get_cache(endpoint.data["configuration_id"], cache_key)
        print(cached_result.data)
        if cached_result.data:
            print("cached data found")
            return cached_result.data["cache_value"]

        start_time = time.time()

        print(start_time)

        print(config.data)
        print(config.data[0]["url"])
        print(config.data[0]["selectors"])

        print(endpoint.data["configuration_id"])

        raw_result = await scrape_url(config.data[0]["url"], config.data[0]["selectors"])
        print(raw_result)
        # Process and validate the scraped data
        processed_result = process_and_validate_data(
            raw_result,
            endpoint.data["data_schema"],
            endpoint.data["transformations"]
        )
        
        end_time = time.time()

        execution_time = end_time - start_time
        create_performance_metric(
            configuration_id=endpoint.data["configuration_id"],
            execution_time=execution_time,
            memory_usage=None  # Implement memory usage tracking if needed
        )

        # Cache the processed result
        set_cache(
            configuration_id=endpoint.data["configuration_id"],
            cache_key=cache_key,
            cache_value=processed_result,
            expires_at=(datetime.utcnow() + timedelta(minutes=15)).isoformat()
        )

        return processed_result
    except Exception as e:
        create_error_log(
            configuration_id=endpoint.data["configuration_id"],
            error_message=str(e),
            stack_trace=None  # Implement stack trace capturing if needed
        )
        raise HTTPException(status_code=500, detail=f"Scraping or processing failed: {str(e)}")

# Endpoint health monitoring
@router.get("/health/{endpoint_url}")
async def endpoint_health(endpoint_url: str):
    try:
        endpoint = get_custom_endpoint(endpoint_url)
        if not endpoint.data:
            return {"status": "not_found"}

        # Check recent performance metrics and error logs
        recent_metrics = get_recent_performance_metrics(endpoint.data["configuration_id"])
        recent_errors = get_recent_error_logs(endpoint.data["configuration_id"])

        avg_execution_time = sum(metric["execution_time"] for metric in recent_metrics) / len(recent_metrics) if recent_metrics else None
        error_rate = len(recent_errors) / len(recent_metrics) if recent_metrics else None

        return {
            "status": "healthy" if error_rate is None or error_rate < 0.1 else "unhealthy",
            "avg_execution_time": avg_execution_time,
            "error_rate": error_rate
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Implement these functions in app/db/database.py


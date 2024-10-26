from supabase import create_client
from app.core.config import settings
from typing import Dict, Any, List
from datetime import datetime, timedelta

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def create_user(email: str, full_name: str, hashed_password: str) -> Dict[str, Any]:
    return supabase.table("users").insert({"email": email, "full_name": full_name, "hashed_password": hashed_password}).execute()

def get_user_by_email(email: str) -> Dict[str, Any]:
    return supabase.table("users").select("*").eq("email", email).single().execute()

def create_crawl_configuration(user_id: str, name: str, url: str, selectors: Dict[str, Any]) -> Dict[str, Any]:
    result = supabase.table("crawl_configurations").insert({
        "user_id": user_id,
        "name": name,
        "url": url,
        "selectors": selectors
    }).execute()
    return result

def get_crawl_configurations(user_id: str) -> List[Dict[str, Any]]:
    return supabase.table("crawl_configurations").select("*").eq("user_id", user_id).execute()

def create_custom_endpoint(user_id: str, endpoint_url: str, configuration_id: str, schema: Dict[str, Any], transformations: Dict[str, str]) -> Dict[str, Any]:
    return supabase.table("custom_endpoints").insert({
        "user_id": user_id,
        "endpoint_url": endpoint_url,
        "configuration_id": configuration_id,
        "schema": schema,
        "transformations": transformations
    }).execute()

def get_custom_endpoint(endpoint_url: str) -> Dict[str, Any]:
    return supabase.table("custom_endpoints").select("*").eq("endpoint_url", endpoint_url).single().execute()

def create_scraping_history(configuration_id: str, status: str, result: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    return supabase.table("scraping_history").insert({
        "configuration_id": configuration_id,
        "status": status,
        "result": result,
        "metadata": metadata
    }).execute()

def create_error_log(configuration_id: str, error_message: str, stack_trace: str) -> Dict[str, Any]:
    return supabase.table("error_logs").insert({
        "configuration_id": configuration_id,
        "error_message": error_message,
        "stack_trace": stack_trace
    }).execute()

def create_performance_metric(configuration_id: str, execution_time: float, memory_usage: float) -> Dict[str, Any]:
    return supabase.table("performance_metrics").insert({
        "configuration_id": configuration_id,
        "execution_time": execution_time,
        "memory_usage": memory_usage
    }).execute()

def set_cache(configuration_id: str, cache_key: str, cache_value: Dict[str, Any], expires_at: str) -> Dict[str, Any]:
    return supabase.table("cache").insert({
        "configuration_id": configuration_id,
        "cache_key": cache_key,
        "cache_value": cache_value,
        "expires_at": expires_at
    }).execute()

def get_cache(configuration_id: str, cache_key: str) -> Dict[str, Any]:
    return supabase.table("cache").select("*").eq("configuration_id", configuration_id).eq("cache_key", cache_key).single().execute()

def get_recent_performance_metrics(configuration_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    return supabase.table("performance_metrics").select("*").eq("configuration_id", configuration_id).order("created_at", desc=True).limit(limit).execute()

def get_recent_error_logs(configuration_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    return supabase.table("error_logs").select("*").eq("configuration_id", configuration_id).order("created_at", desc=True).limit(limit).execute()

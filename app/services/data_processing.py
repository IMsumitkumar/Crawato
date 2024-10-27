from typing import Dict, Any, List
import re
from bs4 import BeautifulSoup
from datetime import datetime
import json

def clean_text(text: str) -> str:
    """Remove extra whitespace and normalize text."""
    return re.sub(r'\s+', ' ', text).strip()

def extract_text_from_html(html: str) -> str:
    """Extract text content from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    return clean_text(soup.get_text())

def parse_date(date_string: str) -> datetime:
    """Parse date string into datetime object."""
    # Add more date formats as needed
    date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y"]
    for format in date_formats:
        try:
            return datetime.strptime(date_string, format)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_string}")

def normalize_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize dictionary keys to snake_case."""
    return {re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower(): value for key, value in data.items()}

def process_scraped_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to process scraped data."""
    processed_data = {}
    
    for key, value in data.items():
        # Normalize keys
        key = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        
        if isinstance(value, str):
            # Clean text and extract from HTML if necessary
            value = extract_text_from_html(value)
            
            # Try to parse dates
            try:
                value = parse_date(value)
            except ValueError:
                pass
        
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            value = process_scraped_data(value)
        
        elif isinstance(value, list):
            # Process list items
            value = [process_scraped_data(item) if isinstance(item, dict) else item for item in value]
        
        processed_data[key] = value
    
    return processed_data

def validate_data(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate processed data against a schema."""
    for key, value_type in schema.items():
        if key not in data:
            return False
        if not isinstance(data[key], value_type):
            return False
    return True

def transform_data(data: Dict[str, Any], transformations: Dict[str, callable]) -> Dict[str, Any]:
    """Apply custom transformations to the data."""
    transformed_data = data.copy()
    for key, transform_func in transformations.items():
        if key in transformed_data:
            transformed_data[key] = transform_func(transformed_data[key])
    return transformed_data

def serialize_data(data: Dict[str, Any]) -> str:
    """Serialize data to JSON string."""
    return json.dumps(data, default=str)

def process_and_validate_data(raw_data: Dict[str, Any], schema: Dict[str, Any], transformations: Dict[str, callable]) -> Dict[str, Any]:
    """Process, validate, and transform scraped data."""
    processed_data = process_scraped_data(raw_data)
    if not validate_data(processed_data, schema):
        raise ValueError("Data does not match the expected schema")
    transformed_data = transform_data(processed_data, transformations)
    return transformed_data


def clean_data(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [clean_data(item) for item in data if item is not None]
    elif isinstance(data, str):
        return data.strip()
    else:
        return data
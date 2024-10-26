import pytest
from app.services.data_processing import (
    clean_text,
    extract_text_from_html,
    parse_date,
    normalize_keys,
    process_scraped_data,
    validate_data,
    transform_data,
    serialize_data,
    process_and_validate_data
)
from datetime import datetime

def test_clean_text():
    assert clean_text("  Hello   World  ") == "Hello World"
    assert clean_text("\n\nTest\t\tString\n") == "Test String"

def test_extract_text_from_html():
    html = "<html><body><h1>Title</h1><p>Paragraph</p></body></html>"
    assert extract_text_from_html(html) == "Title Paragraph"

def test_parse_date():
    assert parse_date("2023-05-01") == datetime(2023, 5, 1)
    assert parse_date("01/05/2023") == datetime(2023, 5, 1)
    assert parse_date("May 1, 2023") == datetime(2023, 5, 1)
    with pytest.raises(ValueError):
        parse_date("Invalid Date")

def test_normalize_keys():
    data = {"FirstName": "John", "LastName": "Doe", "age": 30}
    assert normalize_keys(data) == {"first_name": "John", "last_name": "Doe", "age": 30}

def test_process_scraped_data():
    data = {
        "Title": "<h1>Test Title</h1>",
        "Date": "2023-05-01",
        "Nested": {"SubKey": "SubValue"},
        "List": ["Item1", "Item2"]
    }
    processed = process_scraped_data(data)
    assert processed["title"] == "Test Title"
    assert processed["date"] == datetime(2023, 5, 1)
    assert processed["nested"] == {"sub_key": "SubValue"}
    assert processed["list"] == ["Item1", "Item2"]

def test_validate_data():
    schema = {"name": str, "age": int}
    valid_data = {"name": "John", "age": 30}
    invalid_data = {"name": "John", "age": "30"}
    assert validate_data(valid_data, schema) == True
    assert validate_data(invalid_data, schema) == False

def test_transform_data():
    data = {"name": "john doe", "age": "30"}
    transformations = {
        "name": lambda x: x.title(),
        "age": lambda x: int(x)
    }
    transformed = transform_data(data, transformations)
    assert transformed == {"name": "John Doe", "age": 30}

def test_serialize_data():
    data = {"name": "John", "age": 30, "date": datetime(2023, 5, 1)}
    serialized = serialize_data(data)
    assert '"name": "John"' in serialized
    assert '"age": 30' in serialized
    assert '"date": "2023-05-01 00:00:00"' in serialized

def test_process_and_validate_data():
    raw_data = {
        "Title": "<h1>Test Title</h1>",
        "Date": "2023-05-01",
        "Views": "1000"
    }
    schema = {
        "title": str,
        "date": datetime,
        "views": int
    }
    transformations = {
        "views": lambda x: int(x)
    }
    result = process_and_validate_data(raw_data, schema, transformations)
    assert result == {
        "title": "Test Title",
        "date": datetime(2023, 5, 1),
        "views": 1000
    }

    # Test with invalid data
    invalid_raw_data = {
        "Title": "<h1>Test Title</h1>",
        "Date": "Invalid Date",
        "Views": "1000"
    }
    with pytest.raises(ValueError):
        process_and_validate_data(invalid_raw_data, schema, transformations)

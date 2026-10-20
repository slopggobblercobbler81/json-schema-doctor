"""Tests for utility functions."""

import json
from pathlib import Path
import pytest
import yaml

from json_schema_doctor.utils import (
    dump_data,
    get_json_type,
    infer_string_format,
    load_data,
)


def test_get_json_type():
    assert get_json_type(None) == "null"
    assert get_json_type(True) == "boolean"
    assert get_json_type(False) == "boolean"
    assert get_json_type(42) == "integer"
    assert get_json_type(3.14) == "number"
    assert get_json_type("hello") == "string"
    assert get_json_type([1, 2, 3]) == "array"
    assert get_json_type((1, 2)) == "array"
    assert get_json_type({"a": 1}) == "object"
    assert get_json_type(object()) == "any"


def test_infer_string_format():
    # UUID
    assert infer_string_format("123e4567-e89b-12d3-a456-426614174000") == "uuid"
    assert infer_string_format("C1F727B1-2E99-4D64-883A-D6E6A4B11F0A") == "uuid"

    # Date-Time
    assert infer_string_format("2026-10-20T05:00:00Z") == "date-time"
    assert infer_string_format("2026-10-20T05:00:00+02:00") == "date-time"
    assert infer_string_format("2026-10-20 05:00:00") == "date-time"

    # Date
    assert infer_string_format("2026-10-20") == "date"

    # Time
    assert infer_string_format("14:30:00") == "time"
    assert infer_string_format("14:30:00.123Z") == "time"

    # Email
    assert infer_string_format("test.user+tag@domain.co.uk") == "email"

    # IPv4 / IPv6
    assert infer_string_format("192.168.1.1") == "ipv4"
    assert infer_string_format("::1") == "ipv6"
    assert infer_string_format("2001:0db8:85a3:0000:0000:8a2e:0370:7334") == "ipv6"

    # URI
    assert infer_string_format("https://api.example.com/v1/users?id=1") == "uri"
    assert infer_string_format("ftp://files.example.com/data.csv") == "uri"

    # Non-formatted or invalid
    assert infer_string_format("plain text without format") is None
    assert infer_string_format("") is None
    assert infer_string_format(123) is None


def test_load_data_raw_and_files(tmp_path: Path):
    # Raw JSON string
    assert load_data('{"key": "value"}') == {"key": "value"}
    # Raw YAML string
    assert load_data("key: value\ncount: 5") == {"key": "value", "count": 5}
    # Empty string
    assert load_data("") is None

    # JSON File
    json_file = tmp_path / "test.json"
    json_file.write_text('{"name": "doctor"}', encoding="utf-8")
    assert load_data(json_file) == {"name": "doctor"}

    # YAML File
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: doctor\nscore: 100", encoding="utf-8")
    assert load_data(yaml_file) == {"name": "doctor", "score": 100}

    # JSONL File
    jsonl_file = tmp_path / "test.jsonl"
    jsonl_file.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")
    assert load_data(jsonl_file) == [{"id": 1}, {"id": 2}]

    # Invalid data
    with pytest.raises(ValueError):
        load_data(12345)


def test_dump_data():
    data = {"b": 2, "a": 1}
    # JSON
    json_str = dump_data(data, format="json", sort_keys=True)
    assert json.loads(json_str) == data
    assert json_str.index('"a"') < json_str.index('"b"')

    # YAML
    yaml_str = dump_data(data, format="yaml")
    assert yaml.safe_load(yaml_str) == data

    # JSONL
    list_data = [{"id": 1}, {"id": 2}]
    jsonl_str = dump_data(list_data, format="jsonl")
    lines = jsonl_str.strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": 1}

    # Single item as JSONL
    single_jsonl = dump_data({"id": 1}, format="jsonl")
    assert json.loads(single_jsonl) == {"id": 1}

    # Unsupported format
    with pytest.raises(ValueError):
        dump_data(data, format="unknown")

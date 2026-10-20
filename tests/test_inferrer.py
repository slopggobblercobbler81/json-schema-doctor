"""Tests for SchemaInferrer."""

import pytest
from json_schema_doctor.inferrer import SchemaInferrer


def test_infer_primitives():
    inferrer = SchemaInferrer()

    assert inferrer.infer(None)["type"] == "null"
    assert inferrer.infer(True)["type"] == "boolean"
    assert inferrer.infer(100)["type"] == "integer"
    assert inferrer.infer(99.99)["type"] == "number"
    assert inferrer.infer("simple string")["type"] == "string"


def test_infer_formats():
    inferrer_with_fmt = SchemaInferrer(infer_formats=True)
    inferrer_no_fmt = SchemaInferrer(infer_formats=False)

    schema_email = inferrer_with_fmt.infer("user@example.com")
    assert schema_email["type"] == "string"
    assert schema_email.get("format") == "email"

    schema_no_fmt = inferrer_no_fmt.infer("user@example.com")
    assert "format" not in schema_no_fmt


def test_infer_objects_and_arrays():
    inferrer = SchemaInferrer()
    payload = {
        "id": 1,
        "name": "Widget",
        "tags": ["alpha", "beta"],
        "metadata": {
            "active": True
        }
    }

    schema = inferrer.infer(payload)
    assert schema["type"] == "object"
    assert "properties" in schema
    assert schema["properties"]["id"]["type"] == "integer"
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["tags"]["type"] == "array"
    assert schema["properties"]["tags"]["items"]["type"] == "string"
    assert schema["properties"]["metadata"]["type"] == "object"
    assert schema["properties"]["metadata"]["properties"]["active"]["type"] == "boolean"
    assert sorted(schema["required"]) == ["id", "metadata", "name", "tags"]


def test_infer_from_samples_optional_fields():
    inferrer = SchemaInferrer(mark_all_required=False)
    samples = [
        {"id": 1, "username": "alice", "email": "alice@example.com"},
        {"id": 2, "username": "bob"},  # missing email
    ]

    schema = inferrer.infer_from_samples(samples)
    assert schema["type"] == "object"
    assert "email" in schema["properties"]
    # email is only in sample 1, so it should not be in required
    assert sorted(schema["required"]) == ["id", "username"]


def test_infer_from_samples_mark_all_required():
    inferrer = SchemaInferrer(mark_all_required=True)
    samples = [
        {"id": 1, "username": "alice"},
        {"id": 2, "email": "bob@example.com"},
    ]

    schema = inferrer.infer_from_samples(samples)
    assert sorted(schema["required"]) == ["email", "id", "username"]


def test_infer_type_widening():
    inferrer = SchemaInferrer()
    # Integer and float becomes number
    samples = [
        {"val": 10},
        {"val": 20.5},
    ]
    schema = inferrer.infer_from_samples(samples)
    assert schema["properties"]["val"]["type"] == "number"

    # String and null becomes ["null", "string"]
    samples_nullable = [
        {"note": "hello"},
        {"note": None},
    ]
    schema_nullable = inferrer.infer_from_samples(samples_nullable)
    assert set(schema_nullable["properties"]["note"]["type"]) == {"null", "string"}


def test_infer_enums():
    inferrer = SchemaInferrer(infer_enums=True, enum_threshold=3)
    samples = [
        {"status": "pending"},
        {"status": "active"},
        {"status": "pending"},
        {"status": "active"},
    ]
    schema = inferrer.infer_from_samples(samples)
    assert "enum" in schema["properties"]["status"]
    assert set(schema["properties"]["status"]["enum"]) == {"pending", "active"}


def test_infer_empty_samples():
    inferrer = SchemaInferrer(title="Empty")
    schema = inferrer.infer_from_samples([])
    assert schema["type"] == "object"
    assert schema["title"] == "Empty"

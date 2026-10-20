"""Tests for SchemaDoctor healing engine."""

import pytest
from json_schema_doctor.healer import SchemaDoctor


def test_heal_missing_required():
    base_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "phone": {"type": "string"},
        },
        "required": ["id", "phone"],
    }
    # Payload missing phone
    payload = {"id": 10}

    doctor = SchemaDoctor()
    result = doctor.heal(base_schema, payload, relax_required=True)

    assert result.is_modified is True
    assert "phone" not in result.healed_schema.get("required", [])
    assert result.healed_schema["required"] == ["id"]
    assert any("Made property optional" in c for c in result.changes)


def test_heal_new_property():
    base_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
        },
        "required": ["id"],
    }
    payload = {"id": 1, "description": "New product description"}

    doctor = SchemaDoctor()
    result = doctor.heal(base_schema, payload)

    assert result.is_modified is True
    assert "description" in result.healed_schema["properties"]
    assert result.healed_schema["properties"]["description"]["type"] == "string"
    assert any("Added property '$.description'" in c for c in result.changes)


def test_heal_type_widening():
    base_schema = {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
        },
    }
    payload = {"age": 25.5}

    doctor = SchemaDoctor()
    result = doctor.heal(base_schema, payload)

    assert result.is_modified is True
    assert result.healed_schema["properties"]["age"]["type"] == "number"
    assert any("Widened type at '$.age'" in c for c in result.changes)


def test_heal_nullability():
    base_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
        },
    }
    payload = {"title": None}

    doctor = SchemaDoctor()
    result = doctor.heal(base_schema, payload)

    assert result.is_modified is True
    assert set(result.healed_schema["properties"]["title"]["type"]) == {"null", "string"}
    assert any("Allowed null at '$.title'" in c for c in result.changes)


def test_heal_already_compatible():
    base_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
        },
        "required": ["id"],
    }
    payload = {"id": 1}

    doctor = SchemaDoctor()
    result = doctor.heal(base_schema, payload)

    assert result.is_modified is False
    assert "No changes made" in result.summary()

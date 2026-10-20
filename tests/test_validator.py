"""Tests for SchemaValidator."""

import pytest
from json_schema_doctor.validator import SchemaValidator


def test_validator_success():
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["id"],
    }
    payload = {"id": 1, "email": "alice@example.com"}

    validator = SchemaValidator()
    result = validator.validate(payload, schema)

    assert result.is_valid is True
    assert result.error_count == 0
    assert "Passed" in result.to_terminal(use_color=False)


def test_validator_errors():
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["id"],
    }
    payload = {"id": "not-an-int", "email": "invalid-email"}

    validator = SchemaValidator()
    result = validator.validate(payload, schema)

    assert result.is_valid is False
    assert result.error_count == 2
    d = result.to_dict()
    assert d["is_valid"] is False
    assert len(d["errors"]) == 2

    term_output = result.to_terminal(use_color=False)
    assert "Validation Failed" in term_output
    assert "$.id" in term_output


def test_validator_no_formats():
    schema = {
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
        },
    }
    payload = {"email": "not-a-valid-email"}

    # With format checking disabled
    validator = SchemaValidator(check_formats=False)
    result = validator.validate(payload, schema)
    assert result.is_valid is True

"""Tests for DriftDetector and DriftReport."""

import pytest
from json_schema_doctor.drift import (
    DriftDetector,
    DriftItem,
    DriftReport,
    DriftSeverity,
    DriftType,
)


def test_payload_missing_required():
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
        },
        "required": ["id", "name"],
    }
    payload = {"id": 1}  # Missing 'name'

    detector = DriftDetector()
    report = detector.detect_payload_drift(schema, payload)

    assert report.has_breaking is True
    assert report.breaking_count == 1
    drift = report.drifts[0]
    assert drift.drift_type == DriftType.MISSING_REQUIRED
    assert drift.path == "$.name"


def test_payload_type_mismatch():
    schema = {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
        },
    }
    payload = {"age": "twenty"}

    detector = DriftDetector()
    report = detector.detect_payload_drift(schema, payload)

    assert report.has_breaking is True
    drift = report.drifts[0]
    assert drift.drift_type == DriftType.TYPE_MISMATCH
    assert drift.path == "$.age"


def test_payload_nullability():
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
        },
    }
    payload = {"title": None}

    detector = DriftDetector()
    report = detector.detect_payload_drift(schema, payload)

    assert report.has_breaking is True
    drift = report.drifts[0]
    assert drift.drift_type == DriftType.NULLABILITY_MISMATCH
    assert drift.path == "$.title"


def test_payload_unexpected_property_strict_and_non_strict():
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
        },
    }
    payload = {"id": 1, "extra": "field"}

    detector = DriftDetector()

    # Non-strict: Warning
    report_warning = detector.detect_payload_drift(schema, payload, strict_additional_props=False)
    assert report_warning.has_breaking is False
    assert report_warning.has_warnings is True
    assert report_warning.warning_count == 1
    assert report_warning.drifts[0].severity == DriftSeverity.WARNING

    # Strict: Breaking
    report_strict = detector.detect_payload_drift(schema, payload, strict_additional_props=True)
    assert report_strict.has_breaking is True
    assert report_strict.drifts[0].severity == DriftSeverity.BREAKING


def test_payload_enum_and_format_drift():
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["OPEN", "CLOSED"]},
            "email": {"type": "string", "format": "email"},
        },
    }
    payload = {
        "status": "UNKNOWN",
        "email": "not-an-email",
    }

    detector = DriftDetector()
    report = detector.detect_payload_drift(schema, payload)

    assert report.breaking_count == 1  # enum mismatch
    assert report.warning_count == 1   # format mismatch


def test_payload_nested_array_drift():
    schema = {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {"type": "integer"},
            }
        },
    }
    payload = {"scores": [10, "invalid", 30]}

    detector = DriftDetector()
    report = detector.detect_payload_drift(schema, payload)

    assert report.has_breaking is True
    assert report.drifts[0].path == "$.scores[1]"


def test_schema_to_schema_drift():
    baseline = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "data": {"type": ["string", "null"]},
        },
        "required": ["id"],
    }
    candidate = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "data": {"type": "string"},  # Narrowed type (breaking)
            "new_opt": {"type": "boolean"},  # Added property (warning)
        },
        "required": ["id", "data"],  # data became required (breaking)
    }

    detector = DriftDetector()
    report = detector.detect_schema_drift(baseline, candidate)

    assert report.has_breaking is True
    # name was removed (breaking)
    # data narrowed from [string, null] to string (breaking)
    # data became required (breaking)
    # new_opt was added (warning)
    types = [d.drift_type for d in report.drifts]
    assert DriftType.SCHEMA_PROPERTY_REMOVED in types
    assert DriftType.SCHEMA_REQUIRED_ADDED in types
    assert DriftType.SCHEMA_TYPE_CHANGED in types
    assert DriftType.SCHEMA_PROPERTY_ADDED in types


def test_drift_report_outputs():
    report = DriftReport()
    report.add(
        DriftItem(
            path="$.user.email",
            severity=DriftSeverity.BREAKING,
            drift_type=DriftType.MISSING_REQUIRED,
            message="Field is missing",
            expected="present",
            actual="missing",
        )
    )

    d = report.to_dict()
    assert d["breaking_count"] == 1
    assert d["has_breaking"] is True

    md = report.to_markdown()
    assert "# Schema Drift Analysis Report" in md
    assert "$.user.email" in md

    term = report.to_terminal(use_color=False)
    assert "[BREAKING]" in term
    assert "$.user.email" in term

    # Clean report output
    empty_report = DriftReport()
    assert "No drift detected" in empty_report.to_markdown()
    assert "No schema drifts detected" in empty_report.to_terminal(use_color=False)

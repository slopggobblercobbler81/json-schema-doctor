"""Additional tests to achieve comprehensive branch coverage."""

import json
from pathlib import Path
import pytest

from json_schema_doctor.cli import main
from json_schema_doctor.drift import (
    DriftDetector,
    DriftItem,
    DriftSeverity,
    DriftType,
)
from json_schema_doctor.formatter import Formatter
from json_schema_doctor.healer import SchemaDoctor
from json_schema_doctor.inferrer import SchemaInferrer


def test_inferrer_schema_merging_edge_cases():
    inferrer = SchemaInferrer()

    # s1 empty or s2 empty or equal
    s1 = {"type": "string"}
    assert inferrer.merge_schemas({}, s1) == s1
    assert inferrer.merge_schemas(s1, {}) == s1
    assert inferrer.merge_schemas(s1, s1) == s1

    # merge array items
    arr1 = {"type": "array", "items": {"type": "string"}}
    arr2 = {"type": "array", "items": {"type": "integer"}}
    merged_arr = inferrer.merge_schemas(arr1, arr2)
    assert merged_arr["type"] == "array"
    assert set(merged_arr["items"]["type"]) == {"integer", "string"}

    # arr1 has items, arr2 doesn't
    arr3 = {"type": "array"}
    merged_arr_one_sided = inferrer.merge_schemas(arr1, arr3)
    assert merged_arr_one_sided["items"]["type"] == "string"

    merged_arr_other_sided = inferrer.merge_schemas(arr3, arr1)
    assert merged_arr_other_sided["items"]["type"] == "string"

    # object merged with non-object
    obj = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    prim = {"type": "null"}
    merged_obj_prim = inferrer.merge_schemas(obj, prim)
    assert set(merged_obj_prim["type"]) == {"null", "object"}
    assert "properties" in merged_obj_prim

    merged_prim_obj = inferrer.merge_schemas(prim, obj)
    assert set(merged_prim_obj["type"]) == {"null", "object"}
    assert "properties" in merged_prim_obj

    # formats matching vs differing
    fmt1 = {"type": "string", "format": "email"}
    fmt2 = {"type": "string", "format": "email"}
    assert inferrer.merge_schemas(fmt1, fmt2).get("format") == "email"

    fmt_diff = {"type": "string", "format": "uuid"}
    assert "format" not in inferrer.merge_schemas(fmt1, fmt_diff)

    # enums merging
    enum1 = {"type": "string", "enum": ["a", "b"]}
    enum2 = {"type": "string", "enum": ["b", "c"]}
    merged_enum = inferrer.merge_schemas(enum1, enum2)
    assert merged_enum["enum"] == ["a", "b", "c"]


def test_healer_edge_cases():
    doctor = SchemaDoctor()

    # Enum mismatch and format mismatch healing
    base = {
        "type": "object",
        "properties": {
            "role": {"type": "string", "enum": ["user"]},
            "website": {"type": "string", "format": "uri"},
        },
    }
    payload = {
        "role": "admin",
        "website": "plain string not uri",
    }

    res = doctor.heal(base, payload)
    assert res.is_modified is True
    d = res.to_dict()
    assert d["change_count"] > 0
    assert "admin" in res.healed_schema["properties"]["role"]["enum"]


def test_cli_additional_branches(tmp_path: Path, capsys):
    # Test --fail-on-warning flag
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"type": "object", "properties": {"x": {"type": "integer"}}}), encoding="utf-8")
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"x": 1, "extra_warn": "hi"}), encoding="utf-8")

    code_warn = main([
        "drift",
        "-s",
        str(schema),
        "-p",
        str(payload),
        "--fail-on-warning",
    ])
    assert code_warn == 1

    # Test drift output to file
    out_rep = tmp_path / "report.txt"
    code_file = main([
        "drift",
        "-s",
        str(schema),
        "-p",
        str(payload),
        "-o",
        str(out_rep),
    ])
    assert code_file == 0
    assert out_rep.is_file()

    # Test error when neither payload nor candidate schema provided
    code_missing = main(["drift", "-s", str(schema)])
    assert code_missing == 1

    # Test validate with JSON output format
    code_val = main([
        "validate",
        "-s",
        str(schema),
        "-p",
        str(payload),
        "--format",
        "json",
    ])
    assert code_val == 0
    captured = capsys.readouterr()
    assert '"is_valid": true' in captured.out

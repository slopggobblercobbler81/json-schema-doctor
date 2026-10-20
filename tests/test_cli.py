"""Tests for CLI entry points."""

import json
from pathlib import Path
import pytest
from unittest.mock import patch

from json_schema_doctor.cli import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "json-schema-doctor" in captured.out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "json-schema-doctor" in captured.out


def test_cli_infer(tmp_path: Path, capsys):
    sample = tmp_path / "sample.json"
    sample.write_text('{"id": 1, "email": "test@example.com"}', encoding="utf-8")
    out_schema = tmp_path / "schema.json"

    # Test output to file
    code = main([
        "infer",
        str(sample),
        "-o",
        str(out_schema),
        "--title",
        "TestUser",
    ])
    assert code == 0
    assert out_schema.is_file()
    schema_data = json.loads(out_schema.read_text(encoding="utf-8"))
    assert schema_data["title"] == "TestUser"
    assert "email" in schema_data["properties"]

    # Test output to stdout in YAML
    code_yaml = main([
        "infer",
        str(sample),
        "--yaml",
    ])
    assert code_yaml == 0
    captured = capsys.readouterr()
    assert "type: object" in captured.out


def test_cli_drift_payload(tmp_path: Path, capsys):
    schema = tmp_path / "schema.json"
    schema.write_text(
        json.dumps({
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        }),
        encoding="utf-8",
    )
    payload_valid = tmp_path / "valid.json"
    payload_valid.write_text(json.dumps({"id": 100}), encoding="utf-8")

    payload_invalid = tmp_path / "invalid.json"
    payload_invalid.write_text(json.dumps({"id": "not-an-int"}), encoding="utf-8")

    # Drift check on valid payload
    code_valid = main([
        "drift",
        "-s",
        str(schema),
        "-p",
        str(payload_valid),
        "--fail-on-breaking",
    ])
    assert code_valid == 0

    # Drift check on invalid payload with --fail-on-breaking
    code_invalid = main([
        "drift",
        "-s",
        str(schema),
        "-p",
        str(payload_invalid),
        "--format",
        "json",
        "--fail-on-breaking",
    ])
    assert code_invalid == 1
    captured = capsys.readouterr()
    assert "TYPE_MISMATCH" in captured.out


def test_cli_drift_schema_to_schema(tmp_path: Path, capsys):
    s1 = tmp_path / "s1.json"
    s1.write_text(
        json.dumps({"type": "object", "properties": {"a": {"type": "string"}}}),
        encoding="utf-8",
    )
    s2 = tmp_path / "s2.json"
    s2.write_text(
        json.dumps({"type": "object", "properties": {"b": {"type": "string"}}}),
        encoding="utf-8",
    )

    code = main([
        "drift",
        "-s",
        str(s1),
        "-c",
        str(s2),
        "--format",
        "markdown",
    ])
    assert code == 0
    captured = capsys.readouterr()
    assert "# Schema Drift Analysis Report" in captured.out


def test_cli_validate(tmp_path: Path, capsys):
    schema = tmp_path / "schema.json"
    schema.write_text(
        json.dumps({
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        }),
        encoding="utf-8",
    )
    payload_ok = tmp_path / "ok.json"
    payload_ok.write_text(json.dumps({"id": 1}), encoding="utf-8")

    payload_err = tmp_path / "err.json"
    payload_err.write_text(json.dumps({}), encoding="utf-8")

    # Valid
    assert main(["validate", "-s", str(schema), "-p", str(payload_ok)]) == 0

    # Invalid
    assert main(["validate", "-s", str(schema), "-p", str(payload_err)]) == 1


def test_cli_heal(tmp_path: Path):
    schema = tmp_path / "schema.json"
    schema.write_text(
        json.dumps({
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        }),
        encoding="utf-8",
    )
    payload = tmp_path / "payload.json"
    payload.write_text(
        json.dumps({"id": 1, "new_field": "hello"}),
        encoding="utf-8",
    )
    out_schema = tmp_path / "healed.json"

    code = main([
        "heal",
        "-s",
        str(schema),
        "-p",
        str(payload),
        "-o",
        str(out_schema),
        "--show-diff",
    ])
    assert code == 0
    assert out_schema.is_file()
    healed = json.loads(out_schema.read_text(encoding="utf-8"))
    assert "new_field" in healed["properties"]


def test_cli_format(tmp_path: Path, capsys):
    test_file = tmp_path / "test.json"
    test_file.write_text('{"b": 2, "a": 1}', encoding="utf-8")

    # Check syntax
    assert main(["format", str(test_file), "--check"]) == 0

    # Format in place
    assert main(["format", str(test_file), "-i", "--sort-keys"]) == 0
    content = test_file.read_text(encoding="utf-8")
    assert content.index('"a"') < content.index('"b"')

    # Format to stdout as yaml
    assert main(["format", str(test_file), "--to", "yaml"]) == 0
    captured = capsys.readouterr()
    assert "a: 1" in captured.out


def test_cli_no_command(capsys):
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out

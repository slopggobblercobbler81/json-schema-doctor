"""Tests for Formatter."""

import json
from pathlib import Path
import pytest
import yaml

from json_schema_doctor.formatter import Formatter


def test_format_string_json_to_yaml():
    json_in = '{"service": "api", "port": 8080}'
    yaml_out = Formatter.format_string(json_in, target_format="yaml")
    parsed = yaml.safe_load(yaml_out)
    assert parsed == {"service": "api", "port": 8080}


def test_format_string_yaml_to_json():
    yaml_in = "service: api\nport: 8080"
    json_out = Formatter.format_string(yaml_in, target_format="json", indent=2)
    parsed = json.loads(json_out)
    assert parsed == {"service": "api", "port": 8080}


def test_format_file_in_place(tmp_path: Path):
    file_path = tmp_path / "sample.json"
    file_path.write_text('{"b": 2, "a": 1}', encoding="utf-8")

    success, msg = Formatter.format_file(
        input_path=file_path,
        sort_keys=True,
        indent=4,
        in_place=True,
    )
    assert success is True
    content = file_path.read_text(encoding="utf-8")
    assert content.index('"a"') < content.index('"b"')


def test_format_file_to_new_destination(tmp_path: Path):
    in_file = tmp_path / "sample.json"
    in_file.write_text('{"name": "test"}', encoding="utf-8")
    out_file = tmp_path / "output.yaml"

    success, msg = Formatter.format_file(
        input_path=in_file,
        output_path=out_file,
        target_format="yaml",
    )
    assert success is True
    assert out_file.is_file()
    assert yaml.safe_load(out_file.read_text(encoding="utf-8")) == {"name": "test"}


def test_format_file_not_found():
    success, msg = Formatter.format_file("non_existent_file.json")
    assert success is False
    assert "File not found" in msg


def test_validate_syntax():
    assert Formatter.validate_syntax('{"valid": true}')[0] is True
    assert Formatter.validate_syntax("valid: true\n")[0] is True
    assert Formatter.validate_syntax("{unclosed")[0] is False
    assert Formatter.validate_syntax("invalid: [1, 2")[0] is False

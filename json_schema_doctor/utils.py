"""Utility functions for json-schema-doctor."""

import ipaddress
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlparse

import yaml

# Regex patterns for string format detection
DATETIME_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:?\d{2})?$"
)
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_REGEX = re.compile(r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:?\d{2})?$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def get_json_type(val: Any) -> str:
    """Return JSON schema primitive type for a given Python value."""
    if val is None:
        return "null"
    # Check bool before int because bool is a subclass of int in Python
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, int):
        return "integer"
    if isinstance(val, float):
        return "number"
    if isinstance(val, str):
        return "string"
    if isinstance(val, (list, tuple)):
        return "array"
    if isinstance(val, dict):
        return "object"
    return "any"


def infer_string_format(val: str) -> Optional[str]:
    """Infer string format according to JSON Schema specifications."""
    if not isinstance(val, str) or not val.strip():
        return None

    s = val.strip()

    # UUID
    if UUID_REGEX.match(s):
        return "uuid"

    # Date-Time
    if DATETIME_REGEX.match(s):
        return "date-time"

    # Date
    if DATE_REGEX.match(s):
        return "date"

    # Time
    if TIME_REGEX.match(s):
        return "time"

    # Email
    if EMAIL_REGEX.match(s):
        return "email"

    # IP addresses
    try:
        ip = ipaddress.ip_address(s)
        if isinstance(ip, ipaddress.IPv4Address):
            return "ipv4"
        if isinstance(ip, ipaddress.IPv6Address):
            return "ipv6"
    except ValueError:
        pass

    # URI
    if "://" in s:
        try:
            parsed = urlparse(s)
            if parsed.scheme in ("http", "https", "ftp", "ws", "wss", "sftp") and parsed.netloc:
                return "uri"
        except Exception:
            pass

    return None


def load_data(source: Union[str, Path]) -> Any:
    """Load JSON or YAML data from a file path, raw string, or '-' for stdin."""
    if source == "-":
        content = sys.stdin.read()
        return _parse_raw(content)

    if isinstance(source, Path):
        return _read_file(source)

    if isinstance(source, str):
        trimmed = source.strip()
        # Direct string literals (JSON object or array, or multi-line content)
        if trimmed.startswith(("{", "[")) or "\n" in source:
            return _parse_raw(trimmed)

        # Check if it points to an existing file
        try:
            path_obj = Path(source)
            if path_obj.is_file():
                return _read_file(path_obj)
        except (OSError, ValueError):
            pass

        return _parse_raw(source)

    raise ValueError(f"Unable to load data from source: {source}")


def _read_file(source_path: Path) -> Any:
    text = source_path.read_text(encoding="utf-8")
    ext = source_path.suffix.lower()
    if ext == ".json":
        return json.loads(text)
    if ext in (".yaml", ".yml"):
        return yaml.safe_load(text)
    if ext in (".jsonl", ".ndjson"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return _parse_raw(text)


def _parse_raw(raw_str: str) -> Any:
    """Attempt parsing raw string as JSON, then YAML."""
    raw = raw_str.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            return yaml.safe_load(raw)
        except Exception as e:
            raise ValueError(f"Failed to parse content as JSON or YAML: {e}") from e


def dump_data(
    data: Any,
    format: str = "json",
    indent: int = 2,
    sort_keys: bool = False,
) -> str:
    """Dump Python data structure to formatted string (JSON, YAML, or JSONL)."""
    fmt = format.lower().strip()
    if fmt == "json":
        return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    elif fmt in ("yaml", "yml"):
        return yaml.dump(
            data,
            sort_keys=sort_keys,
            indent=indent,
            default_flow_style=False,
            allow_unicode=True,
        )
    elif fmt in ("jsonl", "ndjson"):
        if isinstance(data, list):
            return "\n".join(
                json.dumps(item, sort_keys=sort_keys, ensure_ascii=False) for item in data
            )
        return json.dumps(data, sort_keys=sort_keys, ensure_ascii=False)
    else:
        raise ValueError(f"Unsupported format: {format}. Supported: json, yaml, jsonl")

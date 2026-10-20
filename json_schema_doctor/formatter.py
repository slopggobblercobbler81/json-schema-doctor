"""High-speed JSON, YAML, and JSONL formatter and converter."""

from pathlib import Path
from typing import Any, Optional, Tuple, Union

from json_schema_doctor.utils import dump_data, load_data


class Formatter:
    """Format and convert between JSON, YAML, and JSONL data formats."""

    @staticmethod
    def format_string(
        content: str,
        target_format: str = "json",
        indent: int = 2,
        sort_keys: bool = False,
    ) -> str:
        """Parse raw content and reformat to target format."""
        data = load_data(content)
        return dump_data(data, format=target_format, indent=indent, sort_keys=sort_keys)

    @staticmethod
    def format_file(
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        target_format: Optional[str] = None,
        indent: int = 2,
        sort_keys: bool = False,
        in_place: bool = False,
    ) -> Tuple[bool, str]:
        """Format an existing file. If in_place is True, rewrites original file."""
        in_p = Path(input_path)
        if not in_p.is_file():
            return False, f"File not found: {input_path}"

        # Determine target format if not specified
        if target_format is None:
            ext = in_p.suffix.lower()
            if ext in (".yaml", ".yml"):
                target_format = "yaml"
            elif ext in (".jsonl", ".ndjson"):
                target_format = "jsonl"
            else:
                target_format = "json"

        try:
            data = load_data(in_p)
            formatted_text = dump_data(data, format=target_format, indent=indent, sort_keys=sort_keys)
        except Exception as e:
            return False, f"Error formatting {input_path}: {e}"

        dest_path = in_p if in_place else (Path(output_path) if output_path else None)

        if dest_path:
            dest_path.write_text(formatted_text, encoding="utf-8")
            return True, f"Formatted output written to: {dest_path}"

        return True, formatted_text

    @staticmethod
    def validate_syntax(source: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """Validate if source is syntactically valid JSON or YAML."""
        try:
            load_data(source)
            return True, None
        except Exception as e:
            return False, str(e)

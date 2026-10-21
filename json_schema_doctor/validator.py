"""JSON Schema validation engine with granular error diagnostics."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import jsonschema
from jsonschema import Draft7Validator, FormatChecker


@dataclass
class ValidationErrorDetail:
    path: str
    message: str
    validator: str
    schema_path: str
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "message": self.message,
            "validator": self.validator,
            "schema_path": self.schema_path,
            "expected": self.expected,
            "actual": self.actual,
        }


class ValidationResult:
    """Outcome of JSON schema validation against payload."""

    def __init__(self, is_valid: bool, errors: Optional[List[ValidationErrorDetail]] = None):
        self.is_valid = is_valid
        self.errors: List[ValidationErrorDetail] = errors or []

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "errors": [e.to_dict() for e in self.errors],
        }

    def to_terminal(self, use_color: bool = True) -> str:
        RED = "\033[91m" if use_color else ""
        GREEN = "\033[92m" if use_color else ""
        BOLD = "\033[1m" if use_color else ""
        RESET = "\033[0m" if use_color else ""

        if self.is_valid:
            return f"{GREEN}{BOLD}✔ Validation Passed:{RESET} Payload is 100% compliant with the schema."

        lines = [
            f"{RED}{BOLD}✖ Validation Failed ({self.error_count} error{'s' if self.error_count != 1 else ''}):{RESET}",
            "",
        ]

        for i, err in enumerate(self.errors, 1):
            lines.append(f"  {i}. {BOLD}{err.path}{RESET} [rule: {err.validator}]")
            lines.append(f"     Error:    {err.message}")
            lines.append(f"     Location: {err.schema_path}")
            if err.expected is not None:
                lines.append(f"     Expected: {err.expected}")
            lines.append("")

        return "\n".join(lines)


class SchemaValidator:
    """Validates payloads against schemas using standard JSON Schema Draft 7 with format checkers."""

    def __init__(self, check_formats: bool = True):
        self.format_checker = FormatChecker() if check_formats else None

    def validate(self, payload: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Validate payload against schema and collect all errors."""
        validator_cls = jsonschema.validators.validator_for(schema)
        # Check if schema is valid
        validator_cls.check_schema(schema)

        validator = validator_cls(schema, format_checker=self.format_checker)
        raw_errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))

        if not raw_errors:
            return ValidationResult(is_valid=True, errors=[])

        details: List[ValidationErrorDetail] = []
        for err in raw_errors:
            path_str = "$"
            if err.path:
                for elem in err.path:
                    if isinstance(elem, int):
                        path_str += f"[{elem}]"
                    else:
                        path_str += f".{elem}"

            schema_path_str = "/".join(str(p) for p in err.schema_path)

            details.append(
                ValidationErrorDetail(
                    path=path_str,
                    message=err.message,
                    validator=err.validator,
                    schema_path=schema_path_str,
                    expected=err.validator_value,
                    actual=err.instance,
                )
            )

        return ValidationResult(is_valid=False, errors=details)


def check_numeric_bounds_coherence(schema: Dict[str, Any]) -> List[str]:
    """Validates that minimum is not strictly greater than maximum in schema properties."""
    issues: List[str] = []
    props = schema.get("properties", {})
    if isinstance(props, dict):
        for prop_name, prop_val in props.items():
            if isinstance(prop_val, dict):
                minimum = prop_val.get("minimum")
                maximum = prop_val.get("maximum")
                if minimum is not None and maximum is not None and minimum > maximum:
                    issues.append(f"Property '{prop_name}' has minimum ({minimum}) > maximum ({maximum})")
    return issues


def check_array_bounds_coherence(schema: Dict[str, Any]) -> List[str]:
    """Validates that minItems is not greater than maxItems in array schema definitions."""
    issues: List[str] = []
    props = schema.get("properties", {})
    if isinstance(props, dict):
        for prop_name, prop_val in props.items():
            if isinstance(prop_val, dict):
                min_items = prop_val.get("minItems")
                max_items = prop_val.get("maxItems")
                if min_items is not None and max_items is not None and min_items > max_items:
                    issues.append(f"Property '{prop_name}' has minItems ({min_items}) > maxItems ({max_items})")
    return issues

def is_string_property(prop: Any) -> bool:
    """Returns True if property schema represents string type."""
    return isinstance(prop, dict) and prop.get("type") == "string"

def is_numeric_property(prop: Any) -> bool:
    """Returns True if property schema represents integer or number."""
    return isinstance(prop, dict) and prop.get("type") in ("number", "integer")

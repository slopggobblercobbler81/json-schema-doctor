"""Schema drift detection engine for comparing schemas against payloads or baseline schemas."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from json_schema_doctor.utils import get_json_type, infer_string_format


class DriftSeverity(str, Enum):
    BREAKING = "BREAKING"
    WARNING = "WARNING"
    INFO = "INFO"


class DriftType(str, Enum):
    MISSING_REQUIRED = "MISSING_REQUIRED"
    UNEXPECTED_PROPERTY = "UNEXPECTED_PROPERTY"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    NULLABILITY_MISMATCH = "NULLABILITY_MISMATCH"
    FORMAT_MISMATCH = "FORMAT_MISMATCH"
    ENUM_MISMATCH = "ENUM_MISMATCH"
    SCHEMA_PROPERTY_REMOVED = "SCHEMA_PROPERTY_REMOVED"
    SCHEMA_PROPERTY_ADDED = "SCHEMA_PROPERTY_ADDED"
    SCHEMA_REQUIRED_ADDED = "SCHEMA_REQUIRED_ADDED"
    SCHEMA_REQUIRED_REMOVED = "SCHEMA_REQUIRED_REMOVED"
    SCHEMA_TYPE_CHANGED = "SCHEMA_TYPE_CHANGED"


@dataclass
class DriftItem:
    path: str
    severity: DriftSeverity
    drift_type: DriftType
    message: str
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "severity": self.severity.value,
            "drift_type": self.drift_type.value,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }


class DriftReport:
    """Aggregated report of schema drifts and breaking changes."""

    def __init__(self, drifts: Optional[List[DriftItem]] = None):
        self.drifts: List[DriftItem] = drifts or []

    def add(self, item: DriftItem) -> None:
        self.drifts.append(item)

    @property
    def has_breaking(self) -> bool:
        return any(d.severity == DriftSeverity.BREAKING for d in self.drifts)

    @property
    def has_warnings(self) -> bool:
        return any(d.severity == DriftSeverity.WARNING for d in self.drifts)

    @property
    def breaking_count(self) -> int:
        return sum(1 for d in self.drifts if d.severity == DriftSeverity.BREAKING)

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.drifts if d.severity == DriftSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for d in self.drifts if d.severity == DriftSeverity.INFO)

    @property
    def total_count(self) -> int:
        return len(self.drifts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_drifts": self.total_count,
            "breaking_count": self.breaking_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "has_breaking": self.has_breaking,
            "drifts": [d.to_dict() for d in self.drifts],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Schema Drift Analysis Report",
            "",
            f"**Total Drifts Detected:** {self.total_count}  ",
            f"- 🔴 **Breaking:** {self.breaking_count}  ",
            f"- 🟡 **Warnings:** {self.warning_count}  ",
            f"- 🔵 **Info:** {self.info_count}  ",
            "",
        ]

        if not self.drifts:
            lines.append("✅ **No drift detected! Schema and payload/candidate are 100% aligned.**")
            return "\n".join(lines)

        lines.extend(
            [
                "| Severity | Drift Type | Path | Message | Expected | Actual |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        for d in self.drifts:
            icon = "🔴" if d.severity == DriftSeverity.BREAKING else ("🟡" if d.severity == DriftSeverity.WARNING else "🔵")
            exp = str(d.expected) if d.expected is not None else "-"
            act = str(d.actual) if d.actual is not None else "-"
            # Escape pipe symbols in markdown table
            exp_esc = exp.replace("|", "\\|")
            act_esc = act.replace("|", "\\|")
            msg_esc = d.message.replace("|", "\\|")
            lines.append(f"| {icon} `{d.severity.value}` | `{d.drift_type.value}` | `{d.path}` | {msg_esc} | `{exp_esc}` | `{act_esc}` |")

        return "\n".join(lines)

    def to_terminal(self, use_color: bool = True) -> str:
        # ANSI color codes
        RED = "\033[91m" if use_color else ""
        YELLOW = "\033[93m" if use_color else ""
        CYAN = "\033[96m" if use_color else ""
        GREEN = "\033[92m" if use_color else ""
        BOLD = "\033[1m" if use_color else ""
        RESET = "\033[0m" if use_color else ""

        lines = [
            f"{BOLD}=== JSON Schema Drift Report ==={RESET}",
            f"Summary: {RED}{self.breaking_count} Breaking{RESET} | {YELLOW}{self.warning_count} Warnings{RESET} | {CYAN}{self.info_count} Info{RESET} (Total: {self.total_count})",
            "",
        ]

        if not self.drifts:
            lines.append(f"{GREEN}✔ No schema drifts detected! Payloads match baseline schema perfectly.{RESET}")
            return "\n".join(lines)

        for d in self.drifts:
            if d.severity == DriftSeverity.BREAKING:
                badge = f"{RED}[BREAKING]{RESET}"
            elif d.severity == DriftSeverity.WARNING:
                badge = f"{YELLOW}[WARNING]{RESET}"
            else:
                badge = f"{CYAN}[INFO]{RESET}"

            lines.append(f"  {badge} {BOLD}{d.path}{RESET} ({d.drift_type.value})")
            lines.append(f"    Message:  {d.message}")
            if d.expected is not None or d.actual is not None:
                lines.append(f"    Expected: {d.expected}  |  Actual: {d.actual}")
            lines.append("")

        return "\n".join(lines)


class DriftDetector:
    """Engine for detecting schema drifts in payloads and candidate schemas."""

    def detect_payload_drift(
        self,
        schema: Dict[str, Any],
        payload: Any,
        strict_additional_props: bool = False,
    ) -> DriftReport:
        """Analyze a payload against a reference JSON schema."""
        report = DriftReport()
        self._check_payload_node(schema, payload, path="$", report=report, strict_props=strict_additional_props)
        return report

    def _check_payload_node(
        self,
        schema: Dict[str, Any],
        val: Any,
        path: str,
        report: DriftReport,
        strict_props: bool,
    ) -> None:
        if not isinstance(schema, dict):
            return

        expected_types = schema.get("type")
        actual_type = get_json_type(val)

        # Nullability check
        if val is None:
            if expected_types is not None:
                allowed_types = (
                    [expected_types] if isinstance(expected_types, str) else list(expected_types)
                )
                if "null" not in allowed_types:
                    report.add(
                        DriftItem(
                            path=path,
                            severity=DriftSeverity.BREAKING,
                            drift_type=DriftType.NULLABILITY_MISMATCH,
                            message=f"Received null value at '{path}', which is non-nullable.",
                            expected=allowed_types,
                            actual="null",
                        )
                    )
            return

        # Type compatibility check
        if expected_types is not None:
            allowed_types = (
                [expected_types] if isinstance(expected_types, str) else list(expected_types)
            )

            # Accept integer when number is expected
            is_compatible = False
            for allowed in allowed_types:
                if actual_type == allowed:
                    is_compatible = True
                    break
                if actual_type == "integer" and allowed == "number":
                    is_compatible = True
                    break

            if not is_compatible:
                report.add(
                    DriftItem(
                        path=path,
                        severity=DriftSeverity.BREAKING,
                        drift_type=DriftType.TYPE_MISMATCH,
                        message=f"Type mismatch at '{path}': expected {allowed_types}, got '{actual_type}'.",
                        expected=allowed_types,
                        actual=actual_type,
                    )
                )
                return

        # Enum check
        if "enum" in schema and schema["enum"]:
            if val not in schema["enum"]:
                report.add(
                    DriftItem(
                        path=path,
                        severity=DriftSeverity.BREAKING,
                        drift_type=DriftType.ENUM_MISMATCH,
                        message=f"Value '{val}' at '{path}' is not in allowed enum values.",
                        expected=schema["enum"],
                        actual=val,
                    )
                )

        # Format check for strings
        if actual_type == "string" and "format" in schema:
            expected_format = schema["format"]
            inferred_fmt = infer_string_format(val)
            if inferred_fmt != expected_format:
                report.add(
                    DriftItem(
                        path=path,
                        severity=DriftSeverity.WARNING,
                        drift_type=DriftType.FORMAT_MISMATCH,
                        message=f"Format mismatch at '{path}': expected '{expected_format}', inferred '{inferred_fmt}'.",
                        expected=expected_format,
                        actual=inferred_fmt,
                    )
                )

        # Object check
        if actual_type == "object" and isinstance(val, dict):
            properties = schema.get("properties", {})
            required_keys = schema.get("required", [])
            disallow_extra = schema.get("additionalProperties") is False or strict_props

            # Check missing required keys
            for req in required_keys:
                if req not in val:
                    field_path = f"{path}.{req}"
                    report.add(
                        DriftItem(
                            path=field_path,
                            severity=DriftSeverity.BREAKING,
                            drift_type=DriftType.MISSING_REQUIRED,
                            message=f"Required property '{req}' is missing at '{field_path}'.",
                            expected="present",
                            actual="missing",
                        )
                    )

            # Check unexpected keys
            for k, child_val in val.items():
                field_path = f"{path}.{k}"
                if k not in properties:
                    sev = DriftSeverity.BREAKING if disallow_extra else DriftSeverity.WARNING
                    report.add(
                        DriftItem(
                            path=field_path,
                            severity=sev,
                            drift_type=DriftType.UNEXPECTED_PROPERTY,
                            message=f"Unexpected property '{k}' detected at '{field_path}'.",
                            expected="not defined in schema",
                            actual="present",
                        )
                    )
                else:
                    self._check_payload_node(
                        properties[k],
                        child_val,
                        path=field_path,
                        report=report,
                        strict_props=strict_props,
                    )

        # Array check
        if actual_type == "array" and isinstance(val, list):
            items_schema = schema.get("items")
            if items_schema:
                for idx, item in enumerate(val):
                    item_path = f"{path}[{idx}]"
                    self._check_payload_node(
                        items_schema,
                        item,
                        path=item_path,
                        report=report,
                        strict_props=strict_props,
                    )

    def detect_schema_drift(
        self,
        baseline: Dict[str, Any],
        candidate: Dict[str, Any],
        path: str = "$",
    ) -> DriftReport:
        """Detect compatibility drift between baseline and candidate schemas."""
        report = DriftReport()
        self._diff_schemas(baseline, candidate, path, report)
        return report

    def _diff_schemas(
        self,
        s1: Dict[str, Any],
        s2: Dict[str, Any],
        path: str,
        report: DriftReport,
    ) -> None:
        if not isinstance(s1, dict) or not isinstance(s2, dict):
            return

        # Compare types
        t1 = s1.get("type")
        t2 = s2.get("type")
        if t1 is not None and t2 is not None:
            set1 = {t1} if isinstance(t1, str) else set(t1)
            set2 = {t2} if isinstance(t2, str) else set(t2)

            # If candidate narrowed types (e.g. baseline allowed ["string", "null"] but candidate only string)
            removed_types = set1 - set2
            added_types = set2 - set1

            if removed_types:
                report.add(
                    DriftItem(
                        path=path,
                        severity=DriftSeverity.BREAKING,
                        drift_type=DriftType.SCHEMA_TYPE_CHANGED,
                        message=f"Types {sorted(list(removed_types))} removed at '{path}' (candidate narrowed allowable types).",
                        expected=sorted(list(set1)),
                        actual=sorted(list(set2)),
                    )
                )
            elif added_types:
                report.add(
                    DriftItem(
                        path=path,
                        severity=DriftSeverity.INFO,
                        drift_type=DriftType.SCHEMA_TYPE_CHANGED,
                        message=f"Types {sorted(list(added_types))} added at '{path}' (candidate broadened allowable types).",
                        expected=sorted(list(set1)),
                        actual=sorted(list(set2)),
                    )
                )

        # Compare object properties
        props1 = s1.get("properties", {})
        props2 = s2.get("properties", {})

        for prop_name, p1_sub in props1.items():
            child_path = f"{path}.{prop_name}"
            if prop_name not in props2:
                report.add(
                    DriftItem(
                        path=child_path,
                        severity=DriftSeverity.BREAKING,
                        drift_type=DriftType.SCHEMA_PROPERTY_REMOVED,
                        message=f"Property '{prop_name}' was removed in candidate schema at '{child_path}'.",
                        expected="defined",
                        actual="removed",
                    )
                )
            else:
                self._diff_schemas(p1_sub, props2[prop_name], child_path, report)

        for prop_name in props2:
            child_path = f"{path}.{prop_name}"
            if prop_name not in props1:
                report.add(
                    DriftItem(
                        path=child_path,
                        severity=DriftSeverity.WARNING,
                        drift_type=DriftType.SCHEMA_PROPERTY_ADDED,
                        message=f"New property '{prop_name}' was added in candidate schema at '{child_path}'.",
                        expected="absent",
                        actual="added",
                    )
                )

        # Compare required fields
        req1 = set(s1.get("required", []))
        req2 = set(s2.get("required", []))

        # Adding new required fields is breaking for existing consumers
        new_required = req2 - req1
        for req in new_required:
            report.add(
                DriftItem(
                    path=f"{path}.{req}",
                    severity=DriftSeverity.BREAKING,
                    drift_type=DriftType.SCHEMA_REQUIRED_ADDED,
                    message=f"Property '{req}' became REQUIRED in candidate schema at '{path}.{req}'.",
                    expected="optional",
                    actual="required",
                )
            )

        # Removing required field is relaxing (backward compatible)
        relaxed_required = req1 - req2
        for req in relaxed_required:
            report.add(
                DriftItem(
                    path=f"{path}.{req}",
                    severity=DriftSeverity.INFO,
                    drift_type=DriftType.SCHEMA_REQUIRED_REMOVED,
                    message=f"Property '{req}' became OPTIONAL in candidate schema at '{path}.{req}'.",
                    expected="required",
                    actual="optional",
                )
            )

        # Compare array items
        items1 = s1.get("items")
        items2 = s2.get("items")
        if items1 and items2:
            self._diff_schemas(items1, items2, f"{path}[]", report)

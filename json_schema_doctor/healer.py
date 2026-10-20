"""Schema healing engine for automatically repairing or updating schemas from payloads."""

import copy
from typing import Any, Dict, List, Optional, Sequence, Union

from json_schema_doctor.drift import DriftDetector, DriftType
from json_schema_doctor.inferrer import SchemaInferrer


class HealResult:
    """Outcome of healing a schema against payload(s)."""

    def __init__(self, healed_schema: Dict[str, Any], changes: List[str]):
        self.healed_schema = healed_schema
        self.changes = changes

    @property
    def is_modified(self) -> bool:
        return len(self.changes) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_modified": self.is_modified,
            "change_count": len(self.changes),
            "changes": self.changes,
            "schema": self.healed_schema,
        }

    def summary(self) -> str:
        if not self.is_modified:
            return "Schema is already fully compatible with payload(s). No changes made."
        lines = [f"Schema healed with {len(self.changes)} update(s):"]
        for c in self.changes:
            lines.append(f"  + {c}")
        return "\n".join(lines)


class SchemaDoctor:
    """Repairs and updates JSON Schemas to accommodate drifted payloads."""

    def __init__(self, infer_formats: bool = True):
        self.inferrer = SchemaInferrer(infer_formats=infer_formats, mark_all_required=False)
        self.drift_detector = DriftDetector()

    def heal(
        self,
        base_schema: Dict[str, Any],
        payloads: Union[Any, Sequence[Any]],
        relax_required: bool = True,
    ) -> HealResult:
        """Heal base_schema by incorporating new types, properties, and relaxed constraints from payloads."""
        samples = payloads if isinstance(payloads, list) else [payloads]
        working_schema = copy.deepcopy(base_schema)
        changes: List[str] = []

        for sample in samples:
            # Detect drifts first
            drift_report = self.drift_detector.detect_payload_drift(working_schema, sample)
            for drift in drift_report.drifts:
                if drift.drift_type == DriftType.MISSING_REQUIRED:
                    if relax_required:
                        if self._remove_required_recursive(working_schema, drift.path):
                            changes.append(f"Made property optional: '{drift.path}'")
                elif drift.drift_type == DriftType.UNEXPECTED_PROPERTY:
                    pass  # Will be added through inference merge
                elif drift.drift_type == DriftType.TYPE_MISMATCH:
                    changes.append(
                        f"Widened type at '{drift.path}': {drift.expected} -> {drift.actual}"
                    )
                elif drift.drift_type == DriftType.NULLABILITY_MISMATCH:
                    changes.append(f"Allowed null at '{drift.path}'")
                elif drift.drift_type == DriftType.ENUM_MISMATCH:
                    if self._add_enum_value_recursive(working_schema, drift.path, drift.actual):
                        changes.append(f"Added enum value '{drift.actual}' at '{drift.path}'")
                elif drift.drift_type == DriftType.FORMAT_MISMATCH:
                    if self._remove_format_recursive(working_schema, drift.path):
                        changes.append(f"Removed strict format constraint at '{drift.path}'")

            # Infer candidate schema from sample
            sample_schema = self.inferrer.infer(sample)

            # Preserve metadata
            root_meta = {
                k: working_schema[k]
                for k in ("$schema", "$id", "title", "description", "definitions", "$defs")
                if k in working_schema
            }

            # Merge
            new_merged = self.inferrer.merge_schemas(working_schema, sample_schema)
            new_merged.update(root_meta)

            # Check for new properties
            self._log_new_properties(working_schema, new_merged, "$", changes)
            working_schema = new_merged

        # De-duplicate changes while maintaining order
        unique_changes = list(dict.fromkeys(changes))
        return HealResult(healed_schema=working_schema, changes=unique_changes)

    def _remove_required_recursive(self, schema: Dict[str, Any], target_path: str) -> bool:
        """Helper to remove a required property at target_path."""
        parts = target_path.strip("$.").split(".")
        curr = schema
        for part in parts[:-1]:
            if isinstance(curr, dict) and "properties" in curr and part in curr["properties"]:
                curr = curr["properties"][part]
            else:
                return False

        last_part = parts[-1]
        if isinstance(curr, dict) and "required" in curr and last_part in curr["required"]:
            curr["required"].remove(last_part)
            if not curr["required"]:
                del curr["required"]
            return True
        return False

    def _add_enum_value_recursive(
        self, schema: Dict[str, Any], target_path: str, new_val: Any
    ) -> bool:
        """Helper to add a new enum value at target_path."""
        parts = target_path.strip("$.").split(".")
        curr = schema
        for part in parts:
            if isinstance(curr, dict) and "properties" in curr and part in curr["properties"]:
                curr = curr["properties"][part]
            else:
                return False
        if isinstance(curr, dict) and "enum" in curr:
            if new_val not in curr["enum"]:
                curr["enum"].append(new_val)
                return True
        return False

    def _remove_format_recursive(self, schema: Dict[str, Any], target_path: str) -> bool:
        """Helper to remove format constraint at target_path."""
        parts = target_path.strip("$.").split(".")
        curr = schema
        for part in parts:
            if isinstance(curr, dict) and "properties" in curr and part in curr["properties"]:
                curr = curr["properties"][part]
            else:
                return False
        if isinstance(curr, dict) and "format" in curr:
            del curr["format"]
            return True
        return False

    def _log_new_properties(
        self, old_schema: Dict[str, Any], new_schema: Dict[str, Any], path: str, changes: List[str]
    ) -> None:
        """Find newly added properties between old and new schema."""
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        for k, sub_s in new_props.items():
            child_path = f"{path}.{k}"
            if k not in old_props:
                t = sub_s.get("type", "any")
                changes.append(f"Added property '{child_path}' (type: {t})")
            else:
                self._log_new_properties(old_props[k], sub_s, child_path, changes)

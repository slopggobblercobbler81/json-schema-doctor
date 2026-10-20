"""JSON Schema inference engine with multi-sample merging, format detection, and enum detection."""

import copy
from typing import Any, Dict, List, Optional, Sequence, Set, Union

from json_schema_doctor.utils import get_json_type, infer_string_format


class SchemaInferrer:
    """Infers standard JSON Schema (Draft 7) from one or more JSON/YAML payloads."""

    def __init__(
        self,
        infer_formats: bool = True,
        infer_enums: bool = False,
        enum_threshold: int = 5,
        mark_all_required: bool = False,
        schema_draft: str = "http://json-schema.org/draft-07/schema#",
        title: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.infer_formats = infer_formats
        self.infer_enums = infer_enums
        self.enum_threshold = enum_threshold
        self.mark_all_required = mark_all_required
        self.schema_draft = schema_draft
        self.title = title
        self.description = description

    def infer(self, payload: Any) -> Dict[str, Any]:
        """Infer JSON schema from a single payload."""
        schema = self._infer_node(payload)
        return self._wrap_root(schema)

    def infer_from_samples(self, samples: Sequence[Any]) -> Dict[str, Any]:
        """Infer and merge JSON schema from multiple sample payloads."""
        if not samples:
            return self._wrap_root({"type": "object"})

        merged_schema = self._infer_node(samples[0])
        for sample in samples[1:]:
            next_schema = self._infer_node(sample)
            merged_schema = self.merge_schemas(merged_schema, next_schema)

        # Post-process enum detection if enabled
        if self.infer_enums:
            self._post_process_enums(merged_schema, samples)

        return self._wrap_root(merged_schema)

    def _wrap_root(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap inferred node with root schema metadata."""
        root: Dict[str, Any] = {"$schema": self.schema_draft}
        if self.title:
            root["title"] = self.title
        if self.description:
            root["description"] = self.description
        root.update(schema)
        return root

    def _infer_node(self, val: Any) -> Dict[str, Any]:
        """Infer schema for an arbitrary value node."""
        jtype = get_json_type(val)

        if jtype == "null":
            return {"type": "null"}

        if jtype == "boolean":
            return {"type": "boolean"}

        if jtype == "integer":
            return {"type": "integer"}

        if jtype == "number":
            return {"type": "number"}

        if jtype == "string":
            node: Dict[str, Any] = {"type": "string"}
            if self.infer_formats:
                fmt = infer_string_format(val)
                if fmt:
                    node["format"] = fmt
            return node

        if jtype == "array":
            node = {"type": "array"}
            if not val:
                return node
            # Infer item schemas and merge them
            item_schemas = [self._infer_node(item) for item in val]
            merged_item = item_schemas[0]
            for s in item_schemas[1:]:
                merged_item = self.merge_schemas(merged_item, s)
            node["items"] = merged_item
            return node

        if jtype == "object":
            properties: Dict[str, Any] = {}
            required: List[str] = []
            for k, v in val.items():
                prop_key = str(k)
                properties[prop_key] = self._infer_node(v)
                required.append(prop_key)

            node = {"type": "object", "properties": properties}
            if required:
                node["required"] = sorted(required)
            return node

        return {}

    def merge_schemas(self, s1: Dict[str, Any], s2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two JSON schemas to create a wider compatible schema."""
        if not s1:
            return copy.deepcopy(s2)
        if not s2:
            return copy.deepcopy(s1)
        if s1 == s2:
            return copy.deepcopy(s1)

        result: Dict[str, Any] = {}

        # Merge types
        t1 = s1.get("type")
        t2 = s2.get("type")

        merged_type = self._merge_types(t1, t2)
        if merged_type is not None:
            result["type"] = merged_type

        # Merge object properties
        has_obj1 = "properties" in s1 or (t1 == "object" or (isinstance(t1, list) and "object" in t1))
        has_obj2 = "properties" in s2 or (t2 == "object" or (isinstance(t2, list) and "object" in t2))

        if has_obj1 and has_obj2:
            props1 = s1.get("properties", {})
            props2 = s2.get("properties", {})
            all_keys = set(props1.keys()) | set(props2.keys())
            merged_props: Dict[str, Any] = {}

            for k in sorted(all_keys):
                if k in props1 and k in props2:
                    merged_props[k] = self.merge_schemas(props1[k], props2[k])
                elif k in props1:
                    merged_props[k] = copy.deepcopy(props1[k])
                else:
                    merged_props[k] = copy.deepcopy(props2[k])

            result["properties"] = merged_props

            req1 = set(s1.get("required", []))
            req2 = set(s2.get("required", []))

            if self.mark_all_required:
                merged_req = sorted(list(req1 | req2))
            else:
                merged_req = sorted(list(req1 & req2))

            if merged_req:
                result["required"] = merged_req
        elif "properties" in s1:
            result["properties"] = copy.deepcopy(s1["properties"])
            if "required" in s1 and self.mark_all_required:
                result["required"] = copy.deepcopy(s1["required"])
        elif "properties" in s2:
            result["properties"] = copy.deepcopy(s2["properties"])
            if "required" in s2 and self.mark_all_required:
                result["required"] = copy.deepcopy(s2["required"])

        # Merge array items
        has_arr1 = "items" in s1 or (t1 == "array" or (isinstance(t1, list) and "array" in t1))
        has_arr2 = "items" in s2 or (t2 == "array" or (isinstance(t2, list) and "array" in t2))

        if has_arr1 and has_arr2:
            items1 = s1.get("items")
            items2 = s2.get("items")
            if items1 and items2:
                result["items"] = self.merge_schemas(items1, items2)
            elif items1:
                result["items"] = copy.deepcopy(items1)
            elif items2:
                result["items"] = copy.deepcopy(items2)
        elif "items" in s1:
            result["items"] = copy.deepcopy(s1["items"])
        elif "items" in s2:
            result["items"] = copy.deepcopy(s2["items"])

        # Merge formats: keep only if both match
        fmt1 = s1.get("format")
        fmt2 = s2.get("format")
        if fmt1 and fmt2 and fmt1 == fmt2:
            result["format"] = fmt1

        # Merge enums
        enum1 = s1.get("enum")
        enum2 = s2.get("enum")
        if enum1 is not None and enum2 is not None:
            # preserve distinct union
            combined = list(dict.fromkeys(enum1 + enum2))
            result["enum"] = combined
        elif enum1 is not None:
            result["enum"] = copy.deepcopy(enum1)
        elif enum2 is not None:
            result["enum"] = copy.deepcopy(enum2)

        return result

    def _merge_types(
        self, t1: Union[None, str, List[str]], t2: Union[None, str, List[str]]
    ) -> Union[None, str, List[str]]:
        """Compute the merged type of two types."""
        if t1 is None:
            return t2
        if t2 is None:
            return t1

        set1 = {t1} if isinstance(t1, str) else set(t1)
        set2 = {t2} if isinstance(t2, str) else set(t2)

        # If one is integer and one is number, unify into number
        if "integer" in set1 and "number" in set2:
            set1.remove("integer")
        if "integer" in set2 and "number" in set1:
            set2.remove("integer")

        combined = sorted(list(set1 | set2))

        if len(combined) == 1:
            return combined[0]
        return combined

    def _post_process_enums(self, schema: Dict[str, Any], samples: Sequence[Any]) -> None:
        """Scan values from samples to detect small cardinality enums."""
        if not isinstance(schema, dict):
            return

        # Helper to collect values for properties
        def collect_values(samples_list: Sequence[Any], path: List[str]) -> List[Any]:
            vals = []
            for item in samples_list:
                curr = item
                for p in path:
                    if isinstance(curr, dict) and p in curr:
                        curr = curr[p]
                    else:
                        curr = None
                        break
                if curr is not None:
                    vals.append(curr)
            return vals

        def walk(sub_schema: Dict[str, Any], current_path: List[str]):
            stype = sub_schema.get("type")
            if stype in ("string", "integer"):
                vals = collect_values(samples, current_path)
                if len(vals) >= self.enum_threshold:
                    unique_vals = list(dict.fromkeys(vals))
                    if 1 < len(unique_vals) <= self.enum_threshold:
                        sub_schema["enum"] = unique_vals
            elif stype == "object" and "properties" in sub_schema:
                for prop_name, prop_schema in sub_schema["properties"].items():
                    walk(prop_schema, current_path + [prop_name])
            elif stype == "array" and "items" in sub_schema:
                # Array items can also be inspected
                pass

        walk(schema, [])

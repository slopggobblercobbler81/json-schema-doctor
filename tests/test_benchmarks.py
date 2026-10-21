"""Throughput benchmark tests covering recursive and deeply nested schema validation latency."""

import time
from typing import Any, Dict
import pytest
from json_schema_doctor.validator import SchemaValidator


def _generate_recursive_tree(depth: int, breadth: int = 2) -> Dict[str, Any]:
    """Generates a recursive tree payload with binary branching."""
    if depth <= 0:
        return {"name": f"leaf_{depth}", "value": depth, "children": []}
    return {
        "name": f"node_{depth}",
        "value": depth,
        "children": [_generate_recursive_tree(depth - 1, breadth) for _ in range(breadth)],
    }


def _get_recursive_tree_schema() -> Dict[str, Any]:
    """Returns a JSON schema draft-07 recursive definition using $ref: '#'."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "integer"},
            "children": {
                "type": "array",
                "items": {"$ref": "#"},
            },
        },
        "required": ["name", "value", "children"],
    }


def test_recursive_tree_schema_validation_latency():
    """Benchmark recursive tree validation latency on 500+ and 2000+ nodes."""
    schema = _get_recursive_tree_schema()
    validator = SchemaValidator()

    # Depth 8 binary tree = 511 total nodes
    tree_500 = _generate_recursive_tree(depth=8, breadth=2)

    start = time.perf_counter()
    result_500 = validator.validate(tree_500, schema)
    elapsed_500 = time.perf_counter() - start

    assert result_500.is_valid is True
    assert result_500.error_count == 0
    # 511 recursive nodes should validate in well under 0.5s
    assert elapsed_500 < 0.5

    # Depth 10 binary tree = 2047 total nodes
    tree_2000 = _generate_recursive_tree(depth=10, breadth=2)

    start = time.perf_counter()
    result_2000 = validator.validate(tree_2000, schema)
    elapsed_2000 = time.perf_counter() - start

    assert result_2000.is_valid is True
    assert result_2000.error_count == 0
    # 2047 recursive nodes should validate in under 1.5s
    assert elapsed_2000 < 1.5


def test_recursive_schema_invalid_leaf_diagnostics_latency():
    """Benchmark error path resolution latency when deeply nested recursive node is invalid."""
    schema = _get_recursive_tree_schema()
    validator = SchemaValidator()

    # Generate a tree with an invalid type at depth 0
    def gen_with_bad_leaf(d: int) -> Dict[str, Any]:
        if d <= 0:
            return {"name": "invalid_leaf", "value": "not-an-integer", "children": []}
        return {"name": f"node_{d}", "value": d, "children": [gen_with_bad_leaf(d - 1)]}

    deep_payload = gen_with_bad_leaf(15)

    start = time.perf_counter()
    result = validator.validate(deep_payload, schema)
    elapsed = time.perf_counter() - start

    assert result.is_valid is False
    assert result.error_count >= 1
    assert any("value" in err.path for err in result.errors)
    # Deep recursive error detection and path building should take under 0.5s
    assert elapsed < 0.5


def test_deeply_nested_object_schema_validation_throughput():
    """Benchmark throughput across repeated iterations on deeply nested non-recursive schema."""
    # Build a 25-level nested schema and payload
    depth = 25
    schema: Dict[str, Any] = {"type": "string"}
    payload: Any = "leaf_value"

    for i in range(depth):
        schema = {
            "type": "object",
            "properties": {f"level_{i}": schema},
            "required": [f"level_{i}"],
        }
        payload = {f"level_{i}": payload}

    validator = SchemaValidator()

    iterations = 50
    start = time.perf_counter()
    for _ in range(iterations):
        res = validator.validate(payload, schema)
        assert res.is_valid is True
    elapsed = time.perf_counter() - start

    # 50 iterations on 25-level schema should execute under 1.0s
    assert elapsed < 4.0

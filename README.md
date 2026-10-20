# json-schema-doctor 🩺

[![CI](https://github.com/slopggobblercobbler81/json-schema-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/slopggobblercobbler81/json-schema-doctor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)

**json-schema-doctor** is a high-speed CLI tool and Python library for detecting schema drifts, validating and formatting JSON/YAML payloads, and generating production-ready JSON Schemas from sample data.

---

## 🌟 Key Features

- 🔍 **Schema Drift Detection**: Catch breaking changes, missing required fields, type mutations, and nullability violations before they hit production.
- 🧬 **Automatic Schema Inference**: Instantly generate clean, robust JSON Schema (Draft 7) from one or multiple sample payloads.
- 🩹 **Auto-Healing**: Automatically upgrade and heal existing schemas to accommodate newly drifted payloads without manual rework.
- ⚡ **High-Speed Validation**: Rich diagnostic reports pointing to exact JSON paths and rule violations.
- 🎨 **Format & Convert**: Easily convert and format between JSON, YAML, and JSON Lines (JSONL) with sort keys, custom indentation, and syntax checking.
- 🖥️ **Developer-First CLI & Clean Python API**: Zero-friction integration into CI/CD pipelines, pre-commit hooks, or microservice stacks.

---

## 📦 Installation

```bash
pip install json-schema-doctor
```

Or install from source:
```bash
git clone https://github.com/slopggobblercobbler81/json-schema-doctor.git
cd json-schema-doctor
pip install .
```

---

## 🚀 Quickstart CLI

### 1. Infer JSON Schema from sample payloads
Generate a unified JSON Schema from one or more JSON or YAML files:

```bash
# Infer schema from a single payload
json-schema-doctor infer user_sample.json -o user.schema.json --title "UserSchema"

# Infer and merge schemas across multiple payloads (detects optional fields automatically)
json-schema-doctor infer sample1.json sample2.yaml -o unified.schema.json

# Infer with enum detection
json-schema-doctor infer event_samples.json --infer-enums --enum-threshold 4
```

### 2. Detect Schema Drift (CI/CD Quality Gate)
Check whether incoming payloads or candidate schemas drift from the baseline schema:

```bash
# Check payload against schema
json-schema-doctor drift -s schema.json -p incoming_payload.json

# Strict mode: fail with exit code 1 if breaking changes exist
json-schema-doctor drift -s schema.json -p incoming_payload.json --fail-on-breaking

# Schema-to-schema drift analysis (e.g., in PR pull requests)
json-schema-doctor drift -s baseline_schema.json -c candidate_schema.json --format markdown -o drift_report.md
```

### 3. Heal a Drifted Schema
Automatically update a schema with new fields and relaxed types from real-world payloads:

```bash
json-schema-doctor heal -s schema.json -p drifted_payload.json -o healed_schema.json --show-diff
```

### 4. Validate Payloads
Validate payloads against a schema with pinpoint diagnostic messages:

```bash
json-schema-doctor validate -s schema.json -p payload.json
```

### 5. Format and Convert JSON / YAML
```bash
# Convert JSON to formatted YAML
json-schema-doctor format config.json --to yaml -o config.yaml

# In-place pretty print JSON
json-schema-doctor format data.json -i --indent 4 --sort-keys

# Validate syntax
json-schema-doctor format data.json --check
```

---

## 💻 Python Library Usage

### Schema Inference
```python
from json_schema_doctor import SchemaInferrer

samples = [
    {"id": "c1f727b1-2e99-4d64-883a-d6e6a4b11f0a", "name": "Alice", "role": "admin", "age": 30},
    {"id": "3b29d4fa-a3bb-40cf-b11a-03593b4a2bf4", "name": "Bob", "role": "viewer"}
]

inferrer = SchemaInferrer(infer_formats=True, infer_enums=True)
schema = inferrer.infer_from_samples(samples)

# 'age' is optional (present only in one sample)
# 'id' is automatically detected as format: uuid
# 'role' is detected as enum: ["admin", "viewer"]
```

### Schema Drift Detection
```python
from json_schema_doctor import DriftDetector

schema = {
    "type": "object",
    "properties": {
        "username": {"type": "string"},
        "age": {"type": "integer"}
    },
    "required": ["username"]
}

payload = {
    "age": "twenty"  # Type mismatch and missing required 'username'
}

detector = DriftDetector()
report = detector.detect_payload_drift(schema, payload)

print("Has breaking drifts:", report.has_breaking)
print(report.to_terminal())
```

### Schema Healing
```python
from json_schema_doctor import SchemaDoctor

base_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"}
    },
    "required": ["id", "name"]
}

# Payload contains a new property and null name
new_payload = {"id": 100, "name": None, "avatar_url": "https://example.com/pic.jpg"}

doctor = SchemaDoctor()
result = doctor.heal(base_schema, new_payload)

print(result.summary())
# Schema healed with 2 update(s):
#   + Allowed null at '$.name'
#   + Added property '$.avatar_url' (type: string)
```

---

## 📊 Drift Severity Classification

| Drift Type | Severity | Description |
| :--- | :--- | :--- |
| `MISSING_REQUIRED` | 🔴 BREAKING | A required property is missing from the payload. |
| `TYPE_MISMATCH` | 🔴 BREAKING | Incompatible type encountered (e.g. `string` instead of `integer`). |
| `NULLABILITY_MISMATCH` | 🔴 BREAKING | Received `null` for a non-nullable property. |
| `ENUM_MISMATCH` | 🔴 BREAKING | Value is outside defined allowable enum values. |
| `SCHEMA_PROPERTY_REMOVED` | 🔴 BREAKING | A property was removed in candidate schema. |
| `SCHEMA_REQUIRED_ADDED` | 🔴 BREAKING | A field became required in candidate schema. |
| `UNEXPECTED_PROPERTY` | 🟡 WARNING | Payload has unmapped fields (Breaking if strict). |
| `FORMAT_MISMATCH` | 🟡 WARNING | String did not conform to detected format constraint. |
| `SCHEMA_PROPERTY_ADDED` | 🟡 WARNING | New optional property added to schema. |
| `SCHEMA_REQUIRED_REMOVED` | 🔵 INFO | Property changed from required to optional. |

---

## 🧪 Testing

Run test suite:

```bash
pytest
```

Generate coverage report:

```bash
pytest --cov=json_schema_doctor --cov-report=term-missing
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

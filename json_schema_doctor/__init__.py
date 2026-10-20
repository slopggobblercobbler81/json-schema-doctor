"""json-schema-doctor: High-speed schema drift detection, JSON/YAML formatting, and schema inference."""

from json_schema_doctor.drift import (
    DriftDetector,
    DriftItem,
    DriftReport,
    DriftSeverity,
    DriftType,
)
from json_schema_doctor.formatter import Formatter
from json_schema_doctor.healer import HealResult, SchemaDoctor
from json_schema_doctor.inferrer import SchemaInferrer
from json_schema_doctor.utils import (
    dump_data,
    get_json_type,
    infer_string_format,
    load_data,
)
from json_schema_doctor.validator import (
    SchemaValidator,
    ValidationErrorDetail,
    ValidationResult,
)

__version__ = "0.1.0"

__all__ = [
    "SchemaInferrer",
    "DriftDetector",
    "DriftReport",
    "DriftItem",
    "DriftSeverity",
    "DriftType",
    "SchemaValidator",
    "ValidationResult",
    "ValidationErrorDetail",
    "SchemaDoctor",
    "HealResult",
    "Formatter",
    "load_data",
    "dump_data",
    "infer_string_format",
    "get_json_type",
    "__version__",
]

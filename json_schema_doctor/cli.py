"""CLI interface for json-schema-doctor."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from json_schema_doctor import __version__
from json_schema_doctor.drift import DriftDetector
from json_schema_doctor.formatter import Formatter
from json_schema_doctor.healer import SchemaDoctor
from json_schema_doctor.inferrer import SchemaInferrer
from json_schema_doctor.utils import dump_data, load_data
from json_schema_doctor.validator import SchemaValidator


def create_parser() -> argparse.ArgumentParser:
    """Build argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="json-schema-doctor",
        description="json-schema-doctor: High-speed schema drift detection, JSON/YAML formatting, and schema inference.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: infer
    infer_parser = subparsers.add_parser(
        "infer",
        aliases=["generate"],
        help="Generate JSON Schema from sample payload(s).",
    )
    infer_parser.add_argument(
        "inputs",
        nargs="+",
        help="Path(s) to JSON or YAML sample file(s), or '-' for stdin.",
    )
    infer_parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout).",
    )
    infer_parser.add_argument(
        "--title",
        help="Title of the generated schema.",
    )
    infer_parser.add_argument(
        "--description",
        help="Description of the generated schema.",
    )
    infer_parser.add_argument(
        "--no-formats",
        action="store_true",
        help="Disable automatic string format inference (date, uuid, email, etc.).",
    )
    infer_parser.add_argument(
        "--infer-enums",
        action="store_true",
        help="Infer enum fields for low-cardinality values.",
    )
    infer_parser.add_argument(
        "--enum-threshold",
        type=int,
        default=5,
        help="Max unique values to qualify as an enum (default: 5).",
    )
    infer_parser.add_argument(
        "--all-required",
        action="store_true",
        help="Mark all encountered properties as required.",
    )
    infer_parser.add_argument(
        "-y",
        "--yaml",
        action="store_true",
        help="Output schema in YAML format instead of JSON.",
    )
    infer_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation spaces for output (default: 2).",
    )

    # Command: drift / diff
    drift_parser = subparsers.add_parser(
        "drift",
        aliases=["diff"],
        help="Detect schema drifts between schema and payload, or between two schemas.",
    )
    drift_parser.add_argument(
        "-s",
        "--schema",
        required=True,
        help="Path to baseline JSON Schema.",
    )
    drift_parser.add_argument(
        "-p",
        "--payload",
        help="Path to payload file (JSON or YAML) to compare against schema.",
    )
    drift_parser.add_argument(
        "-c",
        "--candidate-schema",
        help="Path to candidate JSON Schema for schema-to-schema drift analysis.",
    )
    drift_parser.add_argument(
        "-f",
        "--format",
        choices=["terminal", "json", "markdown"],
        default="terminal",
        help="Output report format (default: terminal).",
    )
    drift_parser.add_argument(
        "-o",
        "--output",
        help="Write report to output file instead of stdout.",
    )
    drift_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat extra/unexpected properties as BREAKING drifts.",
    )
    drift_parser.add_argument(
        "--fail-on-breaking",
        action="store_true",
        help="Exit with code 1 if any breaking drifts are detected.",
    )
    drift_parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit with code 1 if any warning or breaking drifts are detected.",
    )

    # Command: validate / check
    val_parser = subparsers.add_parser(
        "validate",
        aliases=["check"],
        help="Validate JSON/YAML payload against JSON schema.",
    )
    val_parser.add_argument(
        "-s",
        "--schema",
        required=True,
        help="Path to JSON Schema file.",
    )
    val_parser.add_argument(
        "-p",
        "--payload",
        required=True,
        help="Path to payload file (JSON or YAML), or '-' for stdin.",
    )
    val_parser.add_argument(
        "-f",
        "--format",
        choices=["terminal", "json"],
        default="terminal",
        help="Output diagnostics format (default: terminal).",
    )
    val_parser.add_argument(
        "--no-formats",
        action="store_true",
        help="Disable format checker validation.",
    )

    # Command: heal
    heal_parser = subparsers.add_parser(
        "heal",
        help="Automatically update/heal a schema to accommodate drifted payloads.",
    )
    heal_parser.add_argument(
        "-s",
        "--schema",
        required=True,
        help="Path to base JSON Schema.",
    )
    heal_parser.add_argument(
        "-p",
        "--payload",
        nargs="+",
        required=True,
        help="Path(s) to sample payloads to incorporate into the schema.",
    )
    heal_parser.add_argument(
        "-o",
        "--output",
        help="Path to save updated schema (default: stdout).",
    )
    heal_parser.add_argument(
        "-y",
        "--yaml",
        action="store_true",
        help="Output schema in YAML format.",
    )
    heal_parser.add_argument(
        "--no-relax-required",
        action="store_true",
        help="Do not remove missing properties from schema 'required' list.",
    )
    heal_parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Print summary of changes applied to stderr.",
    )

    # Command: format / convert
    fmt_parser = subparsers.add_parser(
        "format",
        aliases=["convert"],
        help="Format, convert, and lint JSON and YAML files.",
    )
    fmt_parser.add_argument(
        "input",
        help="Path to input JSON or YAML file, or '-' for stdin.",
    )
    fmt_parser.add_argument(
        "-o",
        "--output",
        help="Path to write formatted output.",
    )
    fmt_parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Format file in place.",
    )
    fmt_parser.add_argument(
        "--to",
        choices=["json", "yaml", "jsonl"],
        default="json",
        help="Target serialization format (default: json).",
    )
    fmt_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation spaces (default: 2).",
    )
    fmt_parser.add_argument(
        "--sort-keys",
        action="store_true",
        help="Sort dictionary keys alphabetically.",
    )
    fmt_parser.add_argument(
        "--check",
        action="store_true",
        help="Only check syntax validity without reformatting.",
    )

    return parser


def handle_infer(args: argparse.Namespace) -> int:
    samples = []
    for inp in args.inputs:
        data = load_data(inp)
        if isinstance(data, list) and not inp.endswith(".jsonl"):
            # If payload is a list of objects, we can treat each object as a sample
            samples.extend(data)
        else:
            samples.append(data)

    inferrer = SchemaInferrer(
        infer_formats=not args.no_formats,
        infer_enums=args.infer_enums,
        enum_threshold=args.enum_threshold,
        mark_all_required=args.all_required,
        title=args.title,
        description=args.description,
    )

    schema = inferrer.infer_from_samples(samples)
    fmt = "yaml" if args.yaml else "json"
    result_str = dump_data(schema, format=fmt, indent=args.indent)

    if args.output:
        Path(args.output).write_text(result_str, encoding="utf-8")
        print(f"Schema written to: {args.output}")
    else:
        print(result_str)
    return 0


def handle_drift(args: argparse.Namespace) -> int:
    detector = DriftDetector()
    schema = load_data(args.schema)

    if args.payload:
        payload = load_data(args.payload)
        report = detector.detect_payload_drift(
            schema, payload, strict_additional_props=args.strict
        )
    elif args.candidate_schema:
        cand_schema = load_data(args.candidate_schema)
        report = detector.detect_schema_drift(schema, cand_schema)
    else:
        print("Error: Either --payload or --candidate-schema must be provided.", file=sys.stderr)
        return 1

    # Format report
    if args.format == "json":
        output_text = dump_data(report.to_dict(), format="json")
    elif args.format == "markdown":
        output_text = report.to_markdown()
    else:
        output_text = report.to_terminal(use_color=sys.stdout.isatty())

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Drift report written to: {args.output}")
    else:
        print(output_text)

    if args.fail_on_breaking and report.has_breaking:
        return 1
    if args.fail_on_warning and (report.has_breaking or report.has_warnings):
        return 1

    return 0


def handle_validate(args: argparse.Namespace) -> int:
    schema = load_data(args.schema)
    payload = load_data(args.payload)

    validator = SchemaValidator(check_formats=not args.no_formats)
    res = validator.validate(payload, schema)

    if args.format == "json":
        print(dump_data(res.to_dict(), format="json"))
    else:
        print(res.to_terminal(use_color=sys.stdout.isatty()))

    return 0 if res.is_valid else 1


def handle_heal(args: argparse.Namespace) -> int:
    base_schema = load_data(args.schema)
    samples = [load_data(p) for p in args.payload]

    doctor = SchemaDoctor()
    heal_res = doctor.heal(
        base_schema,
        samples,
        relax_required=not args.no_relax_required,
    )

    if args.show_diff:
        print(heal_res.summary(), file=sys.stderr)

    fmt = "yaml" if args.yaml else "json"
    output_str = dump_data(heal_res.healed_schema, format=fmt, indent=2)

    if args.output:
        Path(args.output).write_text(output_str, encoding="utf-8")
        print(f"Healed schema written to: {args.output}")
    else:
        print(output_str)

    return 0


def handle_format(args: argparse.Namespace) -> int:
    if args.check:
        valid, err = Formatter.validate_syntax(args.input)
        if valid:
            print(f"✔ Syntax is valid: {args.input}")
            return 0
        else:
            print(f"✖ Syntax error in {args.input}: {err}", file=sys.stderr)
            return 1

    if args.in_place:
        success, msg = Formatter.format_file(
            input_path=args.input,
            target_format=args.to,
            indent=args.indent,
            sort_keys=args.sort_keys,
            in_place=True,
        )
        if success:
            print(f"✔ In-place formatted: {args.input}")
            return 0
        else:
            print(f"✖ Error: {msg}", file=sys.stderr)
            return 1

    # Reading input and writing to output or stdout
    data = load_data(args.input)
    res_str = dump_data(data, format=args.to, indent=args.indent, sort_keys=args.sort_keys)

    if args.output:
        Path(args.output).write_text(res_str, encoding="utf-8")
        print(f"✔ Formatted output written to: {args.output}")
    else:
        print(res_str)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command in ("infer", "generate"):
        return handle_infer(args)
    elif args.command in ("drift", "diff"):
        return handle_drift(args)
    elif args.command in ("validate", "check"):
        return handle_validate(args)
    elif args.command == "heal":
        return handle_heal(args)
    elif args.command in ("format", "convert"):
        return handle_format(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())

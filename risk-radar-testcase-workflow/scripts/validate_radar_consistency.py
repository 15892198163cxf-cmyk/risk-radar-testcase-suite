#!/usr/bin/env python3
"""Compare two concise radar-result JSON files for semantic route parity."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL = {
    "schema_version",
    "radar_provider",
    "applicability",
    "summary",
    "risks",
    "questions",
    "evidence_boundaries",
}
RISK_FIELDS = (
    "risk_id",
    "title",
    "priority",
    "evidence_type",
    "why_relevant",
    "test_points",
    "source_ids",
)
QUESTION_FIELDS = ("question", "impact", "recommended_answer", "basis")
IDENTITY_FIELDS = ("requirement_fingerprint", "evidence_snapshot_id", "run_id")


def load_result(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    missing = sorted(REQUIRED_TOP_LEVEL - set(result))
    if missing:
        raise ValueError(f"{path}: missing fields: {', '.join(missing)}")
    if not isinstance(result["risks"], list) or not isinstance(result["questions"], list):
        raise ValueError(f"{path}: risks and questions must be arrays")
    return result


def normalize_result(result):
    risks = []
    for index, risk in enumerate(result["risks"], 1):
        missing = [field for field in RISK_FIELDS if field not in risk]
        if missing:
            raise ValueError(f"risk {index} missing fields: {', '.join(missing)}")
        item = {field: risk[field] for field in RISK_FIELDS}
        item["test_points"] = sorted(item["test_points"])
        item["source_ids"] = sorted(item["source_ids"])
        risks.append(item)
    questions = []
    for index, question in enumerate(result["questions"], 1):
        missing = [field for field in QUESTION_FIELDS if field not in question]
        if missing:
            raise ValueError(f"question {index} missing fields: {', '.join(missing)}")
        questions.append({field: question[field] for field in QUESTION_FIELDS})
    return {
        "schema_version": result["schema_version"],
        "radar_provider": result["radar_provider"],
        "applicability": result["applicability"],
        **{field: result.get(field) for field in IDENTITY_FIELDS},
        "risks": sorted(risks, key=lambda item: item["risk_id"]),
        "questions": sorted(questions, key=lambda item: item["question"]),
        "evidence_boundaries": sorted(result["evidence_boundaries"]),
    }


def fingerprint(result):
    encoded = json.dumps(
        normalize_result(result), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compare_results(left, right):
    left_normalized = normalize_result(left)
    right_normalized = normalize_result(right)
    if left_normalized == right_normalized:
        return []
    issues = []
    left_risks = {item["risk_id"]: item for item in left_normalized["risks"]}
    right_risks = {item["risk_id"]: item for item in right_normalized["risks"]}
    missing = sorted(set(left_risks) - set(right_risks))
    extra = sorted(set(right_risks) - set(left_risks))
    if missing:
        issues.append("workflow missing risks: " + ", ".join(missing))
    if extra:
        issues.append("workflow has extra risks: " + ", ".join(extra))
    for risk_id in sorted(set(left_risks) & set(right_risks)):
        if left_risks[risk_id] != right_risks[risk_id]:
            issues.append(f"risk changed: {risk_id}")
    for field in (
        "schema_version",
        "radar_provider",
        "applicability",
        *IDENTITY_FIELDS,
        "questions",
        "evidence_boundaries",
    ):
        if left_normalized[field] != right_normalized[field]:
            issues.append(f"field changed: {field}")
    return issues or ["semantic radar result changed"]


def _sources_by_type(result, evidence_type):
    return {
        source_id
        for risk in result["risks"]
        if risk.get("evidence_type") == evidence_type
        for source_id in risk.get("source_ids", [])
    }


def _regression_identity(field, value):
    """Normalize documented hash spelling only; keep opaque IDs exact."""
    if not isinstance(value, str):
        return value
    if field == "requirement_fingerprint":
        match = re.fullmatch(r"(?:sha256:)?([0-9a-fA-F]{64})", value)
        return match.group(1).lower() if match else value
    if field == "evidence_snapshot_id":
        match = re.fullmatch(r"openviking-bugs[:-]([0-9a-fA-F]{64})", value)
        return f"openviking-bugs:{match.group(1).lower()}" if match else value
    return value


def compare_regression_results(left, right):
    """Check hard evidence invariants across independent, non-deterministic runs."""
    incomparable = []
    warnings = []
    identity_unverified = False
    for field in ("requirement_fingerprint", "evidence_snapshot_id"):
        left_value = left.get(field)
        right_value = right.get(field)
        if left_value and right_value and (
            _regression_identity(field, left_value)
            != _regression_identity(field, right_value)
        ):
            incomparable.append(f"{field} differs")
        elif not left_value or not right_value:
            identity_unverified = True
            warnings.append(f"{field} unavailable; comparability is not proven")
    if incomparable:
        return {"status": "incomparable", "issues": incomparable, "warnings": warnings}

    issues = []
    left_direct = _sources_by_type(left, "direct_history")
    right_direct = _sources_by_type(right, "direct_history")
    right_related = _sources_by_type(right, "related_history")
    missing_direct = sorted(left_direct - right_direct - right_related)
    downgraded_direct = sorted((left_direct - right_direct) & right_related)
    if missing_direct:
        issues.append("direct-history sources disappeared: " + ", ".join(missing_direct))
    if downgraded_direct:
        issues.append("direct-history sources were downgraded: " + ", ".join(downgraded_direct))

    left_related = _sources_by_type(left, "related_history")
    right_history = right_direct | right_related
    missing_related = sorted(left_related - right_history)
    if missing_related:
        warnings.append(
            "related-history sources changed; semantic review required: "
            + ", ".join(missing_related)
        )

    if normalize_result(left) != normalize_result(right):
        warnings.append(
            "risk grouping, wording, questions, or boundaries changed; review retained "
            "failure mechanisms and material test points"
        )
    if left.get("run_id") and left.get("run_id") == right.get("run_id"):
        warnings.append("run_id matches; use --mode exact for same-run views")

    return {
        "status": "regression" if issues else ("unverified" if identity_unverified else "ok"),
        "issues": issues,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate standalone/workflow radar parity")
    parser.add_argument("standalone_result")
    parser.add_argument("workflow_result")
    parser.add_argument("--mode", choices=("exact", "regression"), default="exact")
    args = parser.parse_args()
    try:
        standalone = load_result(args.standalone_result)
        workflow = load_result(args.workflow_result)
        if args.mode == "exact":
            issues = compare_results(standalone, workflow)
        else:
            report = compare_regression_results(standalone, workflow)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[INVALID] {exc}")
        return 1
    if args.mode == "exact":
        if issues:
            print("[MISMATCH] same-run radar views differ")
            for issue in issues:
                print(f"- {issue}")
            return 1
        print(f"[OK] exact radar fingerprint: {fingerprint(standalone)}")
        return 0

    if report["status"] == "incomparable":
        print("[INCOMPARABLE] radar runs use different or unproven inputs")
        for issue in report["issues"]:
            print(f"- {issue}")
        for warning in report["warnings"]:
            print(f"- warning: {warning}")
        return 2
    if report["issues"]:
        print("[REGRESSION] independent radar run lost hard evidence invariants")
        for issue in report["issues"]:
            print(f"- {issue}")
        for warning in report["warnings"]:
            print(f"- warning: {warning}")
        return 1
    if report["status"] == "unverified":
        print("[UNVERIFIED] direct-history invariants checked, but input identity is not proven")
        for warning in report["warnings"]:
            print(f"- review: {warning}")
        return 0
    print("[OK] independent radar run retained direct-history invariants")
    for warning in report["warnings"]:
        print(f"- review: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

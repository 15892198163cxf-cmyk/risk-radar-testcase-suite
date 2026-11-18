#!/usr/bin/env python3
"""Bind a final testcase suite to the canonical radar result, read-only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_radar_consistency import load_result

try:
    import yaml
except ImportError:  # pragma: no cover - JSON remains supported without PyYAML.
    yaml = None


def load_suite(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    value = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text) if yaml else None
    if not isinstance(value, dict):
        raise ValueError(f"{path}: testcase suite must be an object")
    return value


def _string_list(value: Any, label: str, issues: list[str]) -> list[str]:
    if not isinstance(value, list):
        issues.append(f"{label} must be an array")
        return []
    normalized = [str(item).strip() for item in value]
    if any(not item for item in normalized):
        issues.append(f"{label} contains blank value")
    if len(normalized) != len(set(normalized)):
        issues.append(f"{label} contains duplicate values")
    return [item for item in normalized if item]


def validate_consumption(
    radar: dict[str, Any], suite: dict[str, Any], *, strict_trace: bool = False
) -> list[str]:
    issues: list[str] = []
    risks = radar.get("risks", [])
    radar_by_id: dict[str, dict[str, Any]] = {}
    for index, risk in enumerate(risks, start=1):
        risk_id = str(risk.get("risk_id", "")).strip()
        if not risk_id:
            issues.append(f"radar risk {index} missing risk_id")
        elif risk_id in radar_by_id:
            issues.append(f"canonical radar contains duplicate risk_id {risk_id}")
        else:
            radar_by_id[risk_id] = risk

    cases = suite.get("testcases")
    if not isinstance(cases, list):
        return issues + ["final suite testcases must be an array"]
    case_ids: set[str] = set()
    case_by_id: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            issues.append(f"final suite testcase {index} must be an object")
            continue
        case_id = str(case.get("id") or case.get("case_id") or "").strip()
        if not case_id:
            issues.append(f"final suite testcase {index} missing id")
        elif case_id in case_ids:
            issues.append(f"final suite contains duplicate testcase id {case_id}")
        else:
            case_ids.add(case_id)
            case_by_id[case_id] = case

    impact = suite.get("radar_impact")
    if not isinstance(impact, dict):
        return issues + ["final suite missing radar_impact object"]
    items = impact.get("items")
    if not isinstance(items, list):
        return issues + ["radar_impact.items must be an array"]

    point_total = sum(len(risk.get("test_points", [])) for risk in risks)
    if impact.get("risks_received") != len(risks):
        issues.append(
            f"radar_impact.risks_received must equal canonical risk count {len(risks)}"
        )
    if impact.get("test_points_received") != point_total:
        issues.append(
            f"radar_impact.test_points_received must equal canonical test-point count {point_total}"
        )
    accounting = [impact.get(field) for field in ("covered", "excluded", "pending")]
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in accounting):
        issues.append("radar_impact covered/excluded/pending must be non-negative integers")
    elif sum(accounting) != point_total:
        issues.append(
            "radar_impact covered/excluded/pending must account for every canonical test point"
        )

    seen_items: set[str] = set()
    for index, item in enumerate(items, start=1):
        label = f"radar_impact.items[{index}]"
        if not isinstance(item, dict):
            issues.append(f"{label} must be an object")
            continue
        risk_id = str(item.get("risk_id", "")).strip()
        if not risk_id:
            issues.append(f"{label} missing risk_id")
            continue
        if risk_id in seen_items:
            issues.append(f"{label} duplicate risk_id {risk_id}")
        seen_items.add(risk_id)
        canonical = radar_by_id.get(risk_id)
        if canonical is None:
            issues.append(f"{label} references non-canonical risk {risk_id}")
            continue
        if str(item.get("risk_title", "")).strip() != str(canonical.get("title", "")).strip():
            issues.append(f"{label}.risk_title differs from canonical radar")
        evidence_types = set(_string_list(item.get("evidence_types"), f"{label}.evidence_types", issues))
        if evidence_types != {str(canonical.get("evidence_type", "")).strip()}:
            issues.append(f"{label}.evidence_types differs from canonical radar")
        testcase_ids = _string_list(item.get("testcase_ids"), f"{label}.testcase_ids", issues)
        missing = sorted(set(testcase_ids) - case_ids)
        if missing:
            issues.append(f"{label} references missing testcase ids: {', '.join(missing)}")
        for case_id in testcase_ids:
            case = case_by_id.get(case_id)
            if case is None:
                continue
            if "radar_risk_ids" not in case:
                if strict_trace:
                    issues.append(f"{label} references {case_id} without radar_risk_ids trace")
                continue
            traced = {str(value).strip() for value in case.get("radar_risk_ids", [])}
            if risk_id not in traced:
                issues.append(f"{label} references {case_id} without matching radar_risk_ids trace")
            if strict_trace:
                source_ids = set(_string_list(
                    case.get("radar_source_ids"), f"{case_id}.radar_source_ids", issues
                ))
                expected_sources = set(_string_list(
                    canonical.get("source_ids", []),
                    f"canonical {risk_id}.source_ids", issues,
                ))
                missing_sources = sorted(expected_sources - source_ids)
                if missing_sources:
                    issues.append(
                        f"{case_id} missing canonical source ids for {risk_id}: "
                        + ", ".join(missing_sources)
                    )
                evidence_types = set(_string_list(
                    case.get("radar_evidence_types"),
                    f"{case_id}.radar_evidence_types", issues,
                ))
                if str(canonical.get("evidence_type", "")).strip() not in evidence_types:
                    issues.append(f"{case_id} missing canonical evidence type for {risk_id}")

    if not accounting or (accounting[1] == 0 and accounting[2] == 0):
        missing_risks = sorted(set(radar_by_id) - seen_items)
        if missing_risks:
            issues.append("final suite omitted canonical risks: " + ", ".join(missing_risks))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical radar consumption")
    parser.add_argument("radar_result", type=Path)
    parser.add_argument("final_suite", type=Path)
    parser.add_argument(
        "--strict-trace", action="store_true",
        help="Require each mapped testcase to carry canonical risk, source, and evidence trace",
    )
    args = parser.parse_args()
    try:
        radar = load_result(args.radar_result)
        suite = load_suite(args.final_suite)
        issues = validate_consumption(radar, suite, strict_trace=args.strict_trace)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[INVALID] {exc}")
        return 1
    if issues:
        print("[MISMATCH] final suite is not bound to the canonical radar result")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(
        f"[OK] canonical radar consumed: {len(radar['risks'])} risks, "
        f"{sum(len(risk['test_points']) for risk in radar['risks'])} test points"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Report historical source IDs lost while revising an existing testcase suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_radar_consumption import load_suite


def source_regressions(baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    """Match stable titles; do not infer that a new radar must retain old risk IDs."""
    current_by_title: dict[str, list[dict[str, Any]]] = {}
    for case in current.get("testcases", []):
        if isinstance(case, dict) and str(case.get("title", "")).strip():
            current_by_title.setdefault(str(case["title"]).strip(), []).append(case)
    findings: list[dict[str, Any]] = []
    for old in baseline.get("testcases", []):
        if not isinstance(old, dict):
            continue
        title = str(old.get("title", "")).strip()
        matches = current_by_title.get(title, [])
        old_sources = set(map(str, old.get("radar_source_ids") or []))
        if not old_sources:
            continue
        if len(matches) != 1:
            findings.append({
                "old_id": old.get("id"), "new_id": None,
                "title": title, "missing_source_ids": sorted(old_sources),
                "status": "unmatched_title_review_case_rename_or_removal",
            })
            continue
        new = matches[0]
        new_sources = set(map(str, new.get("radar_source_ids") or []))
        new_sources.update(map(str, new.get("historical_source_ids") or []))
        missing = sorted(old_sources - new_sources)
        if missing:
            findings.append({
                "old_id": old.get("id"), "new_id": new.get("id"),
                "title": title, "missing_source_ids": missing,
                "status": "source_missing",
            })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    try:
        findings = source_regressions(load_suite(args.baseline), load_suite(args.current))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[INVALID] {exc}")
        return 1
    if findings:
        print("[REVIEW] historical sources need a carryover decision")
        for finding in findings:
            print(json.dumps(finding, ensure_ascii=False))
        print("Preserve applicable IDs in historical_source_ids, or document why each source no longer applies.")
        return 1
    print("[OK] baseline historical source IDs retain a matching case trace")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

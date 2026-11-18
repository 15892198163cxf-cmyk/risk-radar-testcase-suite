#!/usr/bin/env python3
"""Fail fast on mechanical testcase-generation defects before review or export."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - JSON remains supported without PyYAML.
    yaml = None


NUMBERED_STEP_PATTERN = re.compile(r"(?m)^\s*(\d+)[.、)]\s*\S")
MULTI_ACTION_PATTERNS = (
    r"并(?:保存|提交|确认|点击|调用|检查|查看|刷新|重新|再次|切换|执行)",
    r"后(?:保存|提交|确认|点击|调用|检查|查看|刷新|重新|再次|切换|执行)",
    r"同时(?:保存|提交|确认|点击|调用|检查|查看|刷新|重新|再次|切换|执行)",
    r"(?:打开|进入|输入|选择|点击|提交|调用|刷新|检查|查看|确认).{0,24}、"
    r"(?:打开|进入|输入|选择|点击|提交|调用|刷新|检查|查看|确认)",
)
API_EXPECTATION = re.compile(
    r"(?:接口|API).{0,16}(?:返回|拒绝|成功|失败|报错|状态码|不创建|不写入)",
    flags=re.IGNORECASE,
)
API_ACTION = re.compile(
    r"(?:调用|请求|发送|提交|重放).{0,16}(?:接口|API)|"
    r"(?:接口|API).{0,16}(?:调用|请求|发送|提交|重放)|"
    r"\b(?:GET|POST|PUT|PATCH|DELETE)\b",
    flags=re.IGNORECASE,
)
UI_PERMISSION_EXPECTATION = re.compile(
    r"(?:按钮|入口|页签|菜单|页面).{0,16}(?:隐藏|不显示|不可见|置灰|拒绝访问|不可进入)",
)
PERMISSION_CONTEXT = re.compile(r"无权限|权限不足|越权|鉴权|未授权|permission", flags=re.IGNORECASE)
ALLOWED_TYPES = {"正向", "异常", "边界", "权限", "集成", "安全", "功能"}
# Read-only compatibility for suites created before the current Chinese type
# contract. The generator must still write ALLOWED_TYPES for new suites; these
# values are accepted only so an existing no-radar artifact can be revalidated
# and exported without a format-only migration.
LEGACY_ALLOWED_TYPES = {
    "api_behavior",
    "workflow",
    "data_record",
    "constraint",
    "config",
}
RADAR_REVIEW_ACTIONS = {"增强已有用例", "雷达复核并强化"}
RADAR_ADD_ACTIONS = {"新增用例", "雷达新增用例"}
RADAR_MIXED_ACTIONS = {
    "雷达复核并强化 + 雷达新增用例",
    "雷达复核并强化及新增用例",
}


def load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if yaml is None:
        raise RuntimeError("PyYAML is required to validate YAML files")
    value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError("testcase artifact must be an object")
    return value


def step_count(value: Any) -> int:
    return len(NUMBERED_STEP_PATTERN.findall(value)) if isinstance(value, str) else 0


def _radar_id_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    normalized = [str(item).strip() for item in value]
    if any(not item for item in normalized):
        errors.append(f"{label} contains blank testcase id")
    if len(normalized) != len(set(normalized)):
        errors.append(f"{label} contains duplicate testcase id")
    return [item for item in normalized if item]


def _validate_radar_impact(
    payload: dict[str, Any], cases: list[dict[str, Any]], errors: list[str]
) -> None:
    """Validate local radar accounting without changing the no-radar path."""
    impact = payload.get("radar_impact")
    if impact is None:
        return
    if not isinstance(impact, dict):
        errors.append("radar_impact must be an object")
        return
    items = impact.get("items")
    if not isinstance(items, list):
        errors.append("radar_impact.items must be an array")
        return

    case_ids = {
        str(case.get("id") or case.get("case_id") or "").strip()
        for case in cases
        if str(case.get("id") or case.get("case_id") or "").strip()
    }
    seen_risks: set[str] = set()
    reinforced_all: set[str] = set()
    added_all: set[str] = set()
    contribution_mode = any(
        isinstance(item, dict)
        and ("reinforced_testcase_ids" in item or "added_testcase_ids" in item)
        for item in items
    )

    for index, item in enumerate(items, start=1):
        label = f"radar_impact.items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        risk_id = str(item.get("risk_id", "")).strip()
        if not risk_id:
            errors.append(f"{label} missing risk_id")
        elif risk_id in seen_risks:
            errors.append(f"{label} duplicate risk_id {risk_id}")
        seen_risks.add(risk_id)

        testcase_ids = _radar_id_list(item.get("testcase_ids"), f"{label}.testcase_ids", errors)
        missing_ids = sorted(set(testcase_ids) - case_ids)
        if missing_ids:
            errors.append(f"{label} references missing testcase ids: {', '.join(missing_ids)}")

        if not contribution_mode:
            continue  # Backward-compatible validation for already reviewed artifacts.
        if "reinforced_testcase_ids" not in item or "added_testcase_ids" not in item:
            errors.append(
                f"{label} must contain reinforced_testcase_ids and added_testcase_ids"
            )
            continue
        reinforced = set(
            _radar_id_list(
                item.get("reinforced_testcase_ids"),
                f"{label}.reinforced_testcase_ids",
                errors,
            )
        )
        added = set(
            _radar_id_list(
                item.get("added_testcase_ids"),
                f"{label}.added_testcase_ids",
                errors,
            )
        )
        overlap = sorted(reinforced & added)
        if overlap:
            errors.append(f"{label} classifies ids as both reinforced and added: {', '.join(overlap)}")
        if reinforced | added != set(testcase_ids):
            errors.append(f"{label}.testcase_ids must equal reinforced plus added ids")
        reinforced_all.update(reinforced)
        added_all.update(added)

        action = str(item.get("action", "")).strip()
        expected_actions = (
            RADAR_MIXED_ACTIONS
            if reinforced and added
            else RADAR_ADD_ACTIONS
            if added
            else RADAR_REVIEW_ACTIONS
        )
        if action not in expected_actions:
            errors.append(f"{label}.action does not match its reinforced/added ids")

    if contribution_mode:
        overlap = sorted(reinforced_all & added_all)
        if overlap:
            errors.append(
                "radar_impact classifies testcase ids as both reinforced and added: "
                + ", ".join(overlap)
            )
        for field, actual in (
            ("enhanced_cases", len(reinforced_all)),
            ("added_cases", len(added_all)),
        ):
            if impact.get(field) != actual:
                errors.append(
                    f"radar_impact.{field} must equal derived testcase count {actual}"
                )


def validate(payload: dict[str, Any], mode: str) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    raw_cases = payload.get("testcases")
    if not isinstance(raw_cases, list):
        return ["top-level testcases must be an array"], {"cases": 0}
    cases = [case for case in raw_cases if isinstance(case, dict)]
    if len(cases) != len(raw_cases):
        errors.append("testcases contains non-object rows")
    is_radar_suite = "radar_impact" in payload or any(
        any(
            key in case
            for key in ("radar_risk_ids", "radar_source_ids", "radar_evidence_types")
        )
        for case in cases
    )
    ids: set[str] = set()
    single_step = 0
    multi_action_single_step = 0
    for index, case in enumerate(cases, start=1):
        cid = str(case.get("id") or case.get("case_id") or f"row-{index}")
        if cid in ids:
            errors.append(f"{cid}: duplicate testcase id")
        ids.add(cid)
        for field in ("scene", "title", "precondition", "steps", "expected", "priority"):
            if not str(case.get(field, "")).strip():
                errors.append(f"{cid}: missing {field}")
        if (
            case.get("type")
            and case.get("type") not in ALLOWED_TYPES
            and not (
                not is_radar_suite and case.get("type") in LEGACY_ALLOWED_TYPES
            )
        ):
            errors.append(
                f"{cid}: unsupported type {case.get('type')!r}; "
                f"use one of {sorted(ALLOWED_TYPES)}"
            )
        steps = str(case.get("steps", ""))
        expected = str(case.get("expected", ""))
        count = step_count(steps)
        if count <= 1:
            single_step += 1
            if any(re.search(pattern, steps, flags=re.IGNORECASE) for pattern in MULTI_ACTION_PATTERNS):
                multi_action_single_step += 1
                if mode == "detailed":
                    errors.append(f"{cid}: one numbered step contains multiple executable actions")
        if mode == "detailed" and API_EXPECTATION.search(expected) and not API_ACTION.search(steps):
            errors.append(f"{cid}: expected API outcome has no API action in steps")
        combined = " ".join((str(case.get("title", "")), steps, expected))
        if (
            mode == "detailed"
            and PERMISSION_CONTEXT.search(combined)
            and UI_PERMISSION_EXPECTATION.search(expected)
            and API_EXPECTATION.search(expected)
        ):
            errors.append(f"{cid}: UI permission and API authorization must be separate detailed cases")
    if mode == "detailed" and len(cases) >= 20:
        if single_step / len(cases) >= 0.95 and multi_action_single_step >= 3:
            errors.append(
                "suite: detailed cases are mechanically collapsed into one step "
                f"({single_step}/{len(cases)} single-step; {multi_action_single_step} contain multiple actions)"
            )
    _validate_radar_impact(payload, cases, errors)
    summary = {
        "cases": len(cases),
        "single_step_cases": single_step,
        "multi_action_single_step_cases": multi_action_single_step,
        "errors": len(errors),
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--mode", choices=("standard", "detailed"), required=True)
    args = parser.parse_args()
    try:
        errors, summary = validate(load(args.artifact), args.mode)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print("VALID" if not errors else "INVALID")
    for error in errors:
        print(f"- {error}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

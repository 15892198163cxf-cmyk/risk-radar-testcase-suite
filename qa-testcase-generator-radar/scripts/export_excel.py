# -*- coding: utf-8 -*-
"""
QA 用例 Excel 快速导出脚本
用法: python export_excel.py <json或yaml用例路径> <输出xlsx路径>
示例: python export_excel.py temp/Banner管理.json output/Banner管理_v2.xlsx --mode detailed

精简格式：业务场景、用例标题、前置条件、测试步骤、预期结果、优先级
雷达辅助模式：额外生成简洁的「雷达增益」工作表
样式：蓝底白字表头、边框、自动换行、冻结首行、P0浅红/安全浅橙/历史Bug浅黄
"""
import sys
import os
import argparse
import time
from pathlib import Path

from validate_testcase_quality import load as load_testcase_artifact
from validate_testcase_quality import validate as validate_testcase_quality

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openpyxl', '-q'])
    from openpyxl import Workbook, load_workbook


RADAR_HEADERS = ["风险", "雷达带来的帮助", "处理方式", "覆盖用例", "用例数", "证据类型"]
RADAR_STATUS_LABELS = {
    "applied": "已采用",
    "no_direct_match": "无直接命中",
    "not_applicable": "不适用",
}
RADAR_EVIDENCE_LABELS = {
    "direct_history": "直接历史缺陷",
    "related_history": "相关历史缺陷",
    "business_rule": "业务规则",
    "requirement_risk": "需求风险",
    "test_inference": "测试推导",
    "cluster_risk": "同类风险",
}
RADAR_REVIEW_ACTION = "雷达复核并强化"
RADAR_ADD_ACTION = "雷达新增用例"
RADAR_MIXED_ACTION = "雷达复核并强化 + 雷达新增用例"
RADAR_ACTION_ALIASES = {
    "增强已有用例": RADAR_REVIEW_ACTION,
    RADAR_REVIEW_ACTION: RADAR_REVIEW_ACTION,
    "新增用例": RADAR_ADD_ACTION,
    RADAR_ADD_ACTION: RADAR_ADD_ACTION,
    "雷达复核并强化及新增用例": RADAR_MIXED_ACTION,
    RADAR_MIXED_ACTION: RADAR_MIXED_ACTION,
}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_radar_action(value):
    action = str(value or "").strip() or RADAR_REVIEW_ACTION
    return RADAR_ACTION_ALIASES.get(action, action)


def normalize_radar_impact(data, testcases):
    """读取最终套件内的轻量雷达摘要；不追查外部文件，避免导出阶段额外 I/O。"""
    raw = data.get("radar_impact")
    if raw is not None:
        if not isinstance(raw, dict):
            raise ValueError("radar_impact 必须是对象")
        items = raw.get("items", [])
        if not isinstance(items, list):
            raise ValueError("radar_impact.items 必须是数组")
        normalized_items = []
        contribution_mode = any(
            isinstance(item, dict)
            and ("reinforced_testcase_ids" in item or "added_testcase_ids" in item)
            for item in items
        )
        reinforced_all = set()
        added_all = set()
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                raise ValueError(f"radar_impact.items[{index}] 必须是对象")
            risk_id = str(item.get("risk_id", "")).strip()
            risk_title = str(item.get("risk_title", "")).strip()
            help_text = str(item.get("help", "")).strip()
            if not risk_id or not risk_title or not help_text:
                raise ValueError(
                    f"radar_impact.items[{index}] 缺少 risk_id/risk_title/help"
                )
            testcase_ids = [str(value).strip() for value in _as_list(item.get("testcase_ids")) if str(value).strip()]
            evidence_types = [str(value).strip() for value in _as_list(item.get("evidence_types")) if str(value).strip()]
            action = _normalize_radar_action(item.get("action"))
            if contribution_mode:
                if "reinforced_testcase_ids" not in item or "added_testcase_ids" not in item:
                    raise ValueError(
                        f"radar_impact.items[{index}] 缺少 reinforced_testcase_ids/added_testcase_ids"
                    )
                reinforced = {
                    str(value).strip()
                    for value in _as_list(item.get("reinforced_testcase_ids"))
                    if str(value).strip()
                }
                added = {
                    str(value).strip()
                    for value in _as_list(item.get("added_testcase_ids"))
                    if str(value).strip()
                }
                if reinforced and added:
                    action = RADAR_MIXED_ACTION
                elif added:
                    action = RADAR_ADD_ACTION
                else:
                    action = RADAR_REVIEW_ACTION
                testcase_ids = sorted(reinforced | added)
                reinforced_all.update(reinforced)
                added_all.update(added)
            normalized_items.append(
                {
                    "risk_id": risk_id,
                    "risk_title": risk_title,
                    "help": help_text,
                    "action": action,
                    "testcase_ids": testcase_ids,
                    "evidence_types": evidence_types,
                }
            )
        return {
            "status": str(raw.get("status", "applied")).strip() or "applied",
            "summary": str(raw.get("summary", "")).strip(),
            "risks_received": raw.get("risks_received", len(normalized_items)),
            "test_points_received": raw.get("test_points_received", "-"),
            "covered": raw.get("covered", "-"),
            "excluded": raw.get("excluded", 0),
            "pending": raw.get("pending", 0),
            "enhanced_cases": len(reinforced_all) if contribution_mode else raw.get("enhanced_cases", "-"),
            "added_cases": len(added_all) if contribution_mode else raw.get("added_cases", "-"),
            "items": normalized_items,
        }

    # 兼容仅在用例上保留追溯字段的既有雷达套件。
    grouped = {}
    for testcase in testcases:
        testcase_id = str(testcase.get("id", "")).strip()
        evidence_types = _as_list(testcase.get("radar_evidence_types"))
        for risk_id in _as_list(testcase.get("radar_risk_ids")):
            risk_id = str(risk_id).strip()
            if not risk_id:
                continue
            entry = grouped.setdefault(risk_id, {"testcase_ids": [], "evidence_types": []})
            if testcase_id and testcase_id not in entry["testcase_ids"]:
                entry["testcase_ids"].append(testcase_id)
            for evidence_type in evidence_types:
                value = str(evidence_type).strip()
                if value and value not in entry["evidence_types"]:
                    entry["evidence_types"].append(value)
    if not grouped:
        return None
    return {
        "status": "applied",
        "summary": "雷达风险已合并到最终用例。",
        "risks_received": len(grouped),
        "test_points_received": "-",
        "covered": len(grouped),
        "excluded": 0,
        "pending": 0,
        "enhanced_cases": len({case_id for value in grouped.values() for case_id in value["testcase_ids"]}),
        "added_cases": "-",
        "items": [
            {
                "risk_id": risk_id,
                "risk_title": risk_id,
                "help": "补充该风险对应的检查点",
                "action": RADAR_REVIEW_ACTION,
                "testcase_ids": value["testcase_ids"],
                "evidence_types": value["evidence_types"],
            }
            for risk_id, value in grouped.items()
        ],
    }


def verify_excel(output_path, expected_headers, expected_case_count, radar_impact=None):
    """在同一进程内复核最终工作簿，避免再次导入、重导出和全表渲染。"""
    wb = load_workbook(output_path, read_only=False, data_only=False)
    try:
        expected_sheets = ["testcases"] + (["雷达增益"] if radar_impact else [])
        if wb.sheetnames != expected_sheets:
            raise ValueError(f"导出工作表异常: {wb.sheetnames!r}")
        ws = wb["testcases"]
        actual_headers = [ws.cell(1, col).value for col in range(1, len(expected_headers) + 1)]
        if actual_headers != expected_headers:
            raise ValueError(f"导出表头异常: {actual_headers!r}")
        if ws.max_row != expected_case_count + 1:
            raise ValueError(
                f"导出行数异常: expected={expected_case_count + 1}, actual={ws.max_row}"
            )
        if ws.max_column != len(expected_headers):
            raise ValueError(
                f"导出列数异常: expected={len(expected_headers)}, actual={ws.max_column}"
            )
        if str(ws.freeze_panes) != "A2":
            raise ValueError(f"冻结窗格异常: {ws.freeze_panes!r}")
        title_col = 3 if "功能模块" in expected_headers else 2
        steps_col = 5 if "功能模块" in expected_headers else 4
        expected_col = 6 if "功能模块" in expected_headers else 5
        priority_col = 7 if "功能模块" in expected_headers else 6
        for row in range(2, ws.max_row + 1):
            for col, label in (
                (title_col, "用例标题"),
                (steps_col, "测试步骤"),
                (expected_col, "预期结果"),
                (priority_col, "优先级"),
            ):
                if not str(ws.cell(row, col).value or "").strip():
                    raise ValueError(f"第{row}行{label}为空")
        if radar_impact:
            radar_ws = wb["雷达增益"]
            radar_headers = [radar_ws.cell(5, col).value for col in range(1, len(RADAR_HEADERS) + 1)]
            if radar_headers != RADAR_HEADERS:
                raise ValueError(f"雷达增益表头异常: {radar_headers!r}")
            if radar_ws.max_row != len(radar_impact["items"]) + 5:
                raise ValueError(
                    f"雷达增益行数异常: expected={len(radar_impact['items']) + 5}, "
                    f"actual={radar_ws.max_row}"
                )
            if radar_ws.max_column != len(RADAR_HEADERS):
                raise ValueError(
                    f"雷达增益列数异常: expected={len(RADAR_HEADERS)}, actual={radar_ws.max_column}"
                )
            if str(radar_ws.freeze_panes) != "A6":
                raise ValueError(f"雷达增益冻结窗格异常: {radar_ws.freeze_panes!r}")
    finally:
        wb.close()


def generate_excel(artifact_path, output_path, mode=None):
    """从 JSON/YAML 用例文件生成并复核格式化 Excel。"""
    started = time.perf_counter()
    # === 路径安全校验 ===
    # 允许写入的目录白名单（支持相对路径和绝对路径）
    WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ALLOWED_OUTPUT_DIRS = [
        os.path.join(WORKSPACE_ROOT, "temp"),
        os.path.join(WORKSPACE_ROOT, "output"),
        "temp",
        "output",
    ]
    resolved = os.path.realpath(output_path)
    allowed = False
    for allowed_dir in ALLOWED_OUTPUT_DIRS:
        allowed_path = os.path.realpath(allowed_dir)
        if resolved.startswith(allowed_path + os.sep) or resolved == allowed_path:
            allowed = True
            break
    if not allowed:
        print(f"[DENIED] 输出路径必须在 temp/ 或 output/ 下，拒绝写入: {output_path}")
        sys.exit(1)

    data = load_testcase_artifact(Path(artifact_path))

    # Detailed workflows must fail before writing a workbook when generation has
    # mechanically collapsed steps or broken action/assertion closure. Keeping
    # this optional preserves existing standard-mode callers.
    if mode:
        errors, summary = validate_testcase_quality(data, mode)
        if errors:
            details = "\n".join(f"- {error}" for error in errors)
            raise ValueError(
                f"用例质量校验失败，已阻止导出（{summary['errors']} 项）：\n{details}"
            )

    wb = Workbook()
    ws = wb.active
    ws.title = "testcases"

    # === 检测是否有 module_group 字段 ===
    testcases = data.get('testcases', [])
    has_module_group = any(tc.get('module_group') for tc in testcases)
    radar_impact = normalize_radar_impact(data, testcases)

    # === 表头（有 module_group 时前插「功能模块」列） ===
    if has_module_group:
        headers = ['功能模块', '业务场景', '用例标题', '前置条件', '测试步骤', '预期结果', '优先级']
    else:
        headers = ['业务场景', '用例标题', '前置条件', '测试步骤', '预期结果', '优先级']
    total_cols = len(headers)

    # === 样式定义 ===
    header_font = Font(name='微软雅黑', bold=True, size=11, color='FFFFFF')
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')

    cell_font = Font(name='微软雅黑', size=10)
    wrap_alignment = Alignment(wrap_text=True, vertical='top')

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # P0 高亮（浅红背景）
    p0_fill = PatternFill(start_color='FCE4EC', end_color='FCE4EC', fill_type='solid')
    # 安全用例高亮（浅橙背景）
    security_fill = PatternFill(start_color='FFF3E0', end_color='FFF3E0', fill_type='solid')
    # 历史 Bug 高亮（浅黄背景）
    history_bug_fill = PatternFill(start_color='FFFDE7', end_color='FFFDE7', fill_type='solid')

    # === 写表头 ===
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # === 写数据 ===
    row = 2
    for tc in testcases:
        module_group = tc.get('module_group', '')
        scene = tc.get('scene', '')
        priority = tc.get('priority', '')
        title = tc.get('title', '')

        # 兼容 preconditions（list）和 precondition（str）两种写法
        precondition_raw = tc.get('preconditions', tc.get('precondition', ''))
        if isinstance(precondition_raw, list):
            precondition = '\n'.join([f"{i+1}. {p}" for i, p in enumerate(precondition_raw)])
        else:
            precondition = str(precondition_raw).strip() if precondition_raw else ''

        # 处理 steps 字段（可能是 str 或 list）
        steps_raw = tc.get('steps', '')
        if isinstance(steps_raw, list):
            steps = '\n'.join([f"{i+1}. {s}" for i, s in enumerate(steps_raw)])
        else:
            steps = str(steps_raw).strip()

        # 处理 expected 字段（可能是 str 或 list）
        expected_raw = tc.get('expected', '')
        if isinstance(expected_raw, list):
            expected = '\n'.join([f"{i+1}. {e}" for i, e in enumerate(expected_raw)])
        else:
            expected = str(expected_raw).strip()

        tc_type = tc.get('type', '')
        history_bug = tc.get('history_bug', False)

        if has_module_group:
            ws.cell(row=row, column=1, value=module_group)
            ws.cell(row=row, column=2, value=scene)
            ws.cell(row=row, column=3, value=title)
            ws.cell(row=row, column=4, value=precondition)
            ws.cell(row=row, column=5, value=steps)
            ws.cell(row=row, column=6, value=expected)
            ws.cell(row=row, column=7, value=priority)
        else:
            ws.cell(row=row, column=1, value=scene)
            ws.cell(row=row, column=2, value=title)
            ws.cell(row=row, column=3, value=precondition)
            ws.cell(row=row, column=4, value=steps)
            ws.cell(row=row, column=5, value=expected)
            ws.cell(row=row, column=6, value=priority)

        # 应用通用样式
        for col in range(1, total_cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = cell_font
            cell.alignment = wrap_alignment
            cell.border = thin_border

        # 条件高亮：优先级 P0 > 安全 > 历史Bug > 普通
        if tc_type == '安全':
            for col in range(1, total_cols + 1):
                ws.cell(row=row, column=col).fill = security_fill
        elif priority == 'P0':
            for col in range(1, total_cols + 1):
                ws.cell(row=row, column=col).fill = p0_fill
        elif history_bug:
            for col in range(1, total_cols + 1):
                ws.cell(row=row, column=col).fill = history_bug_fill

        row += 1

    # === 列宽 ===
    if has_module_group:
        col_widths = {'A': 20, 'B': 18, 'C': 30, 'D': 30, 'E': 45, 'F': 45, 'G': 8}
    else:
        col_widths = {'A': 18, 'B': 30, 'C': 30, 'D': 45, 'E': 45, 'F': 8}
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    # === 冻结首行 ===
    ws.freeze_panes = 'A2'

    if radar_impact:
        radar_ws = wb.create_sheet("雷达增益")
        radar_ws.merge_cells("A1:F1")
        title_cell = radar_ws["A1"]
        title_cell.value = "雷达对用例的帮助"
        title_cell.font = Font(name='微软雅黑', bold=True, size=12, color='FFFFFF')
        title_cell.fill = header_fill
        title_cell.alignment = header_alignment

        radar_ws["A2"] = "摘要"
        radar_ws["B2"] = radar_impact["summary"] or "雷达结果已纳入最终用例。"
        radar_ws.merge_cells("B2:F2")
        radar_ws["A3"] = "风险 / 测试点"
        radar_ws["B3"] = f"{radar_impact['risks_received']} / {radar_impact['test_points_received']}"
        radar_ws["C3"] = "雷达复核并强化 / 雷达新增用例"
        radar_ws["D3"] = f"{radar_impact['enhanced_cases']} / {radar_impact['added_cases']}"
        radar_ws["E3"] = "覆盖 / 排除 / 待确认"
        radar_ws["F3"] = f"{radar_impact['covered']} / {radar_impact['excluded']} / {radar_impact['pending']}"
        radar_ws["A4"] = "状态"
        radar_ws["B4"] = RADAR_STATUS_LABELS.get(radar_impact["status"], radar_impact["status"])

        for row_number in (2, 3, 4):
            for col in range(1, 7):
                cell = radar_ws.cell(row=row_number, column=col)
                cell.font = cell_font
                cell.alignment = wrap_alignment
                cell.border = thin_border

        for col, header in enumerate(RADAR_HEADERS, 1):
            cell = radar_ws.cell(row=5, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row_number, item in enumerate(radar_impact["items"], 6):
            values = [
                f"{item['risk_id']} {item['risk_title']}",
                item["help"],
                item["action"],
                "、".join(item["testcase_ids"]) or "-",
                len(item["testcase_ids"]),
                "、".join(RADAR_EVIDENCE_LABELS.get(value, value) for value in item["evidence_types"]) or "-",
            ]
            for col, value in enumerate(values, 1):
                cell = radar_ws.cell(row=row_number, column=col, value=value)
                cell.font = cell_font
                cell.alignment = wrap_alignment
                cell.border = thin_border

        for column, width in {"A": 28, "B": 46, "C": 16, "D": 36, "E": 10, "F": 20}.items():
            radar_ws.column_dimensions[column].width = width
        radar_ws.freeze_panes = "A6"

    # === 保存 ===
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    wb.save(output_path)

    case_count = row - 2
    verify_excel(output_path, headers, case_count, radar_impact)
    duration_seconds = time.perf_counter() - started
    module_name = data.get('module', os.path.basename(artifact_path))
    version = data.get('version', '?')
    print(
        f"[OK] {module_name} v{version} -> {output_path} "
        f"({case_count} cases, {len(wb.sheetnames)} sheets, verified, {duration_seconds:.3f}s)"
    )
    return case_count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="导出 QA 测试用例 Excel")
    parser.add_argument("artifact_path")
    parser.add_argument("output_path")
    parser.add_argument("--mode", choices=("standard", "detailed"))
    args = parser.parse_args()
    try:
        generate_excel(args.artifact_path, args.output_path, args.mode)
    except ValueError as exc:
        print(f"[INVALID] {exc}")
        sys.exit(1)

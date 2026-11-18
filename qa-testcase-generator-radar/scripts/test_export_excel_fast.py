#!/usr/bin/env python3

import json
import tempfile
import time
import unittest
from pathlib import Path

import yaml
from openpyxl import load_workbook

from export_excel import generate_excel


def make_case(index):
    return {
        "id": f"TC-{index:03d}",
        "module_group": "管理系统",
        "scene": "审批",
        "priority": "P0" if index % 3 == 0 else "P1",
        "title": f"审批场景{index}",
        "precondition": "存在一条待审批记录",
        "steps": "1. 打开审批页面\n2. 查看目标记录",
        "expected": "1. 页面加载完成\n2. 目标记录字段完整",
        "type": "功能",
        "fp": ["FP01"],
    }


class FastExportTests(unittest.TestCase):
    def test_json_detailed_export_and_verify_101_cases_under_ten_seconds(self):
        temp_root = Path.cwd() / "temp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            source = root / "suite.json"
            output = root / "suite.xlsx"
            source.write_text(
                json.dumps(
                    {"module": "账号锁定审批", "version": 1, "testcases": [make_case(i) for i in range(1, 102)]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            started = time.perf_counter()
            count = generate_excel(str(source), str(output), "detailed")
            elapsed = time.perf_counter() - started
            self.assertEqual(101, count)
            self.assertTrue(output.is_file())
            self.assertLess(elapsed, 10.0)
            workbook = load_workbook(output, read_only=True)
            try:
                self.assertEqual(["testcases"], workbook.sheetnames)
            finally:
                workbook.close()

    def test_legacy_no_radar_json_and_yaml_export_only_testcases_sheet(self):
        legacy_types = ("api_behavior", "workflow", "data_record", "constraint", "config")
        cases = []
        for index, legacy_type in enumerate(legacy_types, start=1):
            item = make_case(index)
            item["type"] = legacy_type
            cases.append(item)
        payload = {"module": "旧版普通用例", "version": 1, "testcases": cases}

        temp_root = Path.cwd() / "temp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            for suffix in ("json", "yaml"):
                source = root / f"legacy-suite.{suffix}"
                if suffix == "json":
                    source.write_text(
                        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                    )
                else:
                    source.write_text(
                        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                        encoding="utf-8",
                    )
                for mode in ("standard", "detailed"):
                    with self.subTest(suffix=suffix, mode=mode):
                        output = root / f"legacy-suite-{suffix}-{mode}.xlsx"
                        count = generate_excel(str(source), str(output), mode)
                        self.assertEqual(len(cases), count)
                        workbook = load_workbook(output, read_only=True)
                        try:
                            self.assertEqual(["testcases"], workbook.sheetnames)
                            self.assertEqual(len(cases) + 1, workbook["testcases"].max_row)
                        finally:
                            workbook.close()

    def test_radar_export_adds_concise_impact_sheet_under_ten_seconds(self):
        temp_root = Path.cwd() / "temp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            source = root / "radar-suite.json"
            output = root / "radar-suite.xlsx"
            payload = {
                "module": "账号锁定审批",
                "version": 1,
                "radar_impact": {
                    "status": "applied",
                    "summary": "补充权限绕过与并发重复提交风险。",
                    "risks_received": 2,
                    "test_points_received": 4,
                    "covered": 4,
                    "excluded": 0,
                    "pending": 0,
                    "enhanced_cases": 3,
                    "added_cases": 1,
                    "items": [
                        {
                            "risk_id": "RISK-001",
                            "risk_title": "接口权限绕过",
                            "help": "补充绕过页面直接调用接口的服务端鉴权检查",
                            "action": "增强已有用例",
                            "testcase_ids": ["TC-001", "TC-002"],
                            "reinforced_testcase_ids": ["TC-001", "TC-002"],
                            "added_testcase_ids": [],
                            "evidence_types": ["direct_history"],
                        },
                        {
                            "risk_id": "RISK-002",
                            "risk_title": "重复提交副作用",
                            "help": "补充并发审批下状态、授权、日志和通知唯一性检查",
                            "action": "雷达复核并强化 + 雷达新增用例",
                            "testcase_ids": ["TC-003", "TC-004"],
                            "reinforced_testcase_ids": ["TC-003"],
                            "added_testcase_ids": ["TC-004"],
                            "evidence_types": ["test_inference"],
                        },
                    ],
                },
                "testcases": [make_case(i) for i in range(1, 102)],
            }
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            started = time.perf_counter()
            count = generate_excel(str(source), str(output), "detailed")
            elapsed = time.perf_counter() - started
            self.assertEqual(101, count)
            self.assertLess(elapsed, 10.0)
            workbook = load_workbook(output, read_only=False, data_only=False)
            try:
                self.assertEqual(["testcases", "雷达增益"], workbook.sheetnames)
                radar_sheet = workbook["雷达增益"]
                self.assertEqual("雷达对用例的帮助", radar_sheet["A1"].value)
                self.assertEqual("2 / 4", radar_sheet["B3"].value)
                self.assertEqual("雷达复核并强化 / 雷达新增用例", radar_sheet["C3"].value)
                self.assertEqual("3 / 1", radar_sheet["D3"].value)
                self.assertEqual("4 / 0 / 0", radar_sheet["F3"].value)
                self.assertEqual("已采用", radar_sheet["B4"].value)
                self.assertEqual("雷达复核并强化", radar_sheet["C6"].value)
                self.assertEqual("雷达复核并强化 + 雷达新增用例", radar_sheet["C7"].value)
                self.assertEqual("直接历史缺陷", radar_sheet["F6"].value)
                self.assertEqual("A6", str(radar_sheet.freeze_panes))
                self.assertEqual(7, radar_sheet.max_row)
            finally:
                workbook.close()


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3

import copy
import unittest

from validate_testcase_quality import validate


def case(case_id: str = "TC-001"):
    return {
        "id": case_id,
        "scene": "权限",
        "title": "无权限成员新增被拒",
        "precondition": "成员无新增权限",
        "steps": "1. 打开页面\n2. 检查新增按钮",
        "expected": "新增按钮不显示",
        "priority": "P0",
        "type": "权限",
    }


class QualityValidationTests(unittest.TestCase):
    def test_valid_detailed_case(self):
        self.assertEqual([], validate({"testcases": [case()]}, "detailed")[0])

    def test_rejects_single_step_with_multiple_actions(self):
        item = case()
        item["steps"] = "1. 输入名称并提交"
        self.assertTrue(any(
            "multiple executable actions" in error
            for error in validate({"testcases": [item]}, "detailed")[0]
        ))

    def test_rejects_api_expectation_without_api_action(self):
        item = case()
        item["expected"] = "新增按钮隐藏，接口返回无权限"
        errors, _ = validate({"testcases": [item]}, "detailed")
        self.assertTrue(any("no API action" in error for error in errors))

    def test_rejects_combined_ui_and_api_permission_case(self):
        item = case()
        item["steps"] = "1. 打开页面\n2. 调用新增接口"
        item["expected"] = "新增按钮隐藏，接口返回无权限"
        errors, _ = validate({"testcases": [item]}, "detailed")
        self.assertTrue(any("must be separate" in error for error in errors))

    def test_rejects_mechanical_suite_collapse(self):
        items = []
        for index in range(20):
            item = copy.deepcopy(case(f"TC-{index:03d}"))
            item["steps"] = "1. 输入名称并提交"
            items.append(item)
        errors, summary = validate({"testcases": items}, "detailed")
        self.assertEqual(20, summary["single_step_cases"])
        self.assertTrue(any("mechanically collapsed" in error for error in errors))

    def test_rejects_unknown_internal_type(self):
        item = case()
        item["type"] = "接口"
        self.assertTrue(any(
            "unsupported type" in error
            for error in validate({"testcases": [item]}, "detailed")[0]
        ))

    def test_accepts_known_legacy_types_for_no_radar_suite(self):
        items = []
        for index, legacy_type in enumerate(
            ("api_behavior", "workflow", "data_record", "constraint", "config"),
            start=1,
        ):
            item = case(f"TC-{index:03d}")
            item["type"] = legacy_type
            items.append(item)
        self.assertEqual([], validate({"testcases": items}, "detailed")[0])

    def test_new_radar_suite_still_rejects_legacy_type(self):
        item = case()
        item["type"] = "workflow"
        payload = {
            "testcases": [item],
            "radar_impact": {
                "enhanced_cases": 1,
                "added_cases": 0,
                "items": [{
                    "risk_id": "RR-01",
                    "action": "雷达复核并强化",
                    "testcase_ids": ["TC-001"],
                }],
            },
        }
        self.assertTrue(any(
            "unsupported type" in error
            for error in validate(payload, "detailed")[0]
        ))

    def test_accepts_verifiable_mixed_radar_accounting(self):
        second = case("TC-002")
        payload = {
            "testcases": [case(), second],
            "radar_impact": {
                "enhanced_cases": 1,
                "added_cases": 1,
                "items": [{
                    "risk_id": "RR-01",
                    "action": "雷达复核并强化 + 雷达新增用例",
                    "testcase_ids": ["TC-001", "TC-002"],
                    "reinforced_testcase_ids": ["TC-001"],
                    "added_testcase_ids": ["TC-002"],
                }],
            },
        }
        self.assertEqual([], validate(payload, "detailed")[0])

    def test_rejects_inconsistent_radar_accounting(self):
        payload = {
            "testcases": [case()],
            "radar_impact": {
                "enhanced_cases": 2,
                "added_cases": 0,
                "items": [{
                    "risk_id": "RR-01",
                    "action": "雷达复核并强化",
                    "testcase_ids": ["TC-001", "TC-MISSING"],
                    "reinforced_testcase_ids": ["TC-001"],
                    "added_testcase_ids": ["TC-001"],
                }],
            },
        }
        errors, _ = validate(payload, "detailed")
        self.assertTrue(any("references missing testcase ids" in error for error in errors))
        self.assertTrue(any("both reinforced and added" in error for error in errors))
        self.assertTrue(any("enhanced_cases must equal" in error for error in errors))

    def test_keeps_legacy_radar_artifact_compatible(self):
        payload = {
            "testcases": [case()],
            "radar_impact": {
                "enhanced_cases": 1,
                "added_cases": 0,
                "items": [{
                    "risk_id": "RR-01",
                    "action": "雷达复核并强化",
                    "testcase_ids": ["TC-001"],
                }],
            },
        }
        self.assertEqual([], validate(payload, "detailed")[0])


if __name__ == "__main__":
    unittest.main()

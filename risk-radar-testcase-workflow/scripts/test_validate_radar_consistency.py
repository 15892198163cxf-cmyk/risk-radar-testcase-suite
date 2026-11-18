#!/usr/bin/env python3

import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_radar_consistency.py")
SPEC = importlib.util.spec_from_file_location("radar_consistency", SCRIPT)
CONSISTENCY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CONSISTENCY)


def result_fixture():
    return {
        "schema_version": "1.0",
        "radar_provider": "ziniao-landmine-map",
        "applicability": "applicable",
        "requirement_fingerprint": "req-sha256",
        "evidence_snapshot_id": "bugs-sha256",
        "run_id": "run-001",
        "summary": "presentation text may differ",
        "risks": [
            {
                "risk_id": "RISK-001",
                "title": "账号锁定不可绕过",
                "priority": "high",
                "evidence_type": "direct_history",
                "why_relevant": "同一执行链",
                "test_points": ["插件未就绪时仍保持锁定", "脚本调用不能绕过保护"],
                "source_ids": ["7002059071", "6840383639"],
            }
        ],
        "questions": [
            {
                "question": "何时刷新状态？",
                "impact": "影响锁定恢复时机",
                "recommended_answer": "主动刷新审批状态",
                "basis": "用户确认",
            }
        ],
        "evidence_boundaries": ["历史缺陷只证明曾发生过"],
    }


class RadarConsistencyTests(unittest.TestCase):
    def test_order_and_summary_wording_do_not_change_semantic_identity(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        right["summary"] = "short workflow presentation"
        right["risks"][0]["source_ids"].reverse()
        right["risks"][0]["test_points"].reverse()
        self.assertEqual([], CONSISTENCY.compare_results(left, right))
        self.assertEqual(CONSISTENCY.fingerprint(left), CONSISTENCY.fingerprint(right))

    def test_missing_direct_history_risk_is_a_hard_mismatch(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        right["risks"] = []
        self.assertIn("workflow missing risks: RISK-001", CONSISTENCY.compare_results(left, right))

    def test_changed_test_point_is_a_hard_mismatch(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        right["risks"][0]["test_points"] = ["只检查页面按钮"]
        self.assertIn("risk changed: RISK-001", CONSISTENCY.compare_results(left, right))

    def test_independent_regrouping_with_same_direct_sources_is_allowed(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        right["run_id"] = "run-002"
        right["risks"][0]["risk_id"] = "RISK-NEW"
        right["risks"][0]["title"] = "保护链路异常时仍保持锁定"
        right["risks"][0]["test_points"] = ["依赖异常和脚本路径均不能放行"]
        report = CONSISTENCY.compare_regression_results(left, right)
        self.assertEqual("ok", report["status"])
        self.assertEqual([], report["issues"])

    def test_independent_run_losing_direct_source_is_regression(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        right["run_id"] = "run-002"
        right["risks"] = []
        report = CONSISTENCY.compare_regression_results(left, right)
        self.assertEqual("regression", report["status"])
        self.assertTrue(any("7002059071" in issue for issue in report["issues"]))

    def test_independent_run_may_add_risks(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        right["run_id"] = "run-002"
        extra = copy.deepcopy(right["risks"][0])
        extra["risk_id"] = "RISK-002"
        extra["title"] = "新增的需求风险"
        extra["evidence_type"] = "test_inference"
        extra["source_ids"] = []
        right["risks"].append(extra)
        report = CONSISTENCY.compare_regression_results(left, right)
        self.assertEqual("ok", report["status"])
        self.assertEqual([], report["issues"])

    def test_different_requirement_fingerprint_is_incomparable(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        right["run_id"] = "run-002"
        right["requirement_fingerprint"] = "another-requirement"
        report = CONSISTENCY.compare_regression_results(left, right)
        self.assertEqual("incomparable", report["status"])
        self.assertIn("requirement_fingerprint differs", report["issues"])

    def test_equivalent_hash_spellings_remain_comparable(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        digest = "a" * 64
        left["requirement_fingerprint"] = "sha256:" + digest.upper()
        right["requirement_fingerprint"] = digest
        left["evidence_snapshot_id"] = "openviking-bugs:" + digest
        right["evidence_snapshot_id"] = "openviking-bugs-" + digest
        right["risks"] = []
        report = CONSISTENCY.compare_regression_results(left, right)
        self.assertEqual("regression", report["status"])
        self.assertTrue(any("direct-history sources disappeared" in issue for issue in report["issues"]))

    def test_legacy_results_without_identity_are_unverified_not_equal(self):
        left = result_fixture()
        right = copy.deepcopy(left)
        for field in CONSISTENCY.IDENTITY_FIELDS:
            left.pop(field, None)
            right.pop(field, None)
        report = CONSISTENCY.compare_regression_results(left, right)
        self.assertEqual("unverified", report["status"])
        self.assertEqual([], report["issues"])


if __name__ == "__main__":
    unittest.main()

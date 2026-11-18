#!/usr/bin/env python3

import copy
import unittest

from validate_radar_consumption import validate_consumption


def radar_fixture():
    return {
        "risks": [{
            "risk_id": "RR-01",
            "title": "权限入口与接口不一致",
            "evidence_type": "direct_history",
            "source_ids": ["BUG-1"],
            "test_points": ["检查入口", "直接调用接口"],
        }],
    }


def suite_fixture():
    return {
        "testcases": [{
            "id": "TC-001", "radar_risk_ids": ["RR-01"],
            "radar_source_ids": ["BUG-1"],
            "radar_evidence_types": ["direct_history"],
        }],
        "radar_impact": {
            "risks_received": 1,
            "test_points_received": 2,
            "covered": 2,
            "excluded": 0,
            "pending": 0,
            "items": [{
                "risk_id": "RR-01",
                "risk_title": "权限入口与接口不一致",
                "testcase_ids": ["TC-001"],
                "evidence_types": ["direct_history"],
            }],
        },
    }


class RadarConsumptionTests(unittest.TestCase):
    def test_accepts_suite_bound_to_canonical_radar(self):
        self.assertEqual([], validate_consumption(radar_fixture(), suite_fixture()))

    def test_rejects_hard_coded_counts(self):
        suite = suite_fixture()
        suite["radar_impact"]["test_points_received"] = 3
        self.assertTrue(any(
            "canonical test-point count" in issue
            for issue in validate_consumption(radar_fixture(), suite)
        ))

    def test_rejects_changed_risk_identity_and_evidence(self):
        suite = suite_fixture()
        item = suite["radar_impact"]["items"][0]
        item["risk_title"] = "重新概括的另一项风险"
        item["evidence_types"] = ["test_inference"]
        issues = validate_consumption(radar_fixture(), suite)
        self.assertTrue(any("risk_title differs" in issue for issue in issues))
        self.assertTrue(any("evidence_types differs" in issue for issue in issues))

    def test_rejects_missing_or_untraced_testcase_reference(self):
        suite = suite_fixture()
        suite["radar_impact"]["items"][0]["testcase_ids"] = ["TC-MISSING"]
        self.assertTrue(any(
            "references missing testcase ids" in issue
            for issue in validate_consumption(radar_fixture(), suite)
        ))
        suite = suite_fixture()
        suite["testcases"][0]["radar_risk_ids"] = ["RR-OTHER"]
        self.assertTrue(any(
            "without matching radar_risk_ids trace" in issue
            for issue in validate_consumption(radar_fixture(), suite)
        ))

    def test_rejects_omitted_risk_when_nothing_is_excluded_or_pending(self):
        suite = suite_fixture()
        suite["radar_impact"]["items"] = []
        self.assertTrue(any(
            "omitted canonical risks" in issue
            for issue in validate_consumption(radar_fixture(), suite)
        ))

    def test_rejects_unaccounted_test_points(self):
        suite = suite_fixture()
        suite["radar_impact"]["covered"] = 1
        self.assertTrue(any(
            "account for every canonical test point" in issue
            for issue in validate_consumption(radar_fixture(), suite)
        ))

    def test_strict_trace_rejects_missing_case_metadata(self):
        suite = suite_fixture()
        case = suite["testcases"][0]
        del case["radar_risk_ids"]
        del case["radar_source_ids"]
        del case["radar_evidence_types"]
        issues = validate_consumption(radar_fixture(), suite, strict_trace=True)
        self.assertTrue(any("without radar_risk_ids trace" in issue for issue in issues))

    def test_strict_trace_rejects_missing_source_and_evidence(self):
        suite = suite_fixture()
        case = suite["testcases"][0]
        case["radar_source_ids"] = []
        case["radar_evidence_types"] = []
        issues = validate_consumption(radar_fixture(), suite, strict_trace=True)
        self.assertTrue(any("missing canonical source ids" in issue for issue in issues))
        self.assertTrue(any("missing canonical evidence type" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()

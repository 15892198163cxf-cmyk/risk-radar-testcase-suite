#!/usr/bin/env python3

import unittest

from audit_suite_revision import source_regressions


class SuiteRevisionTests(unittest.TestCase):
    def test_reports_lost_sources_after_case_id_changes(self):
        before = {"testcases": [{
            "id": "TC-1", "title": "首次申请到达", "radar_source_ids": ["BUG-1"]
        }]}
        after = {"testcases": [{"id": "TC-2", "title": "首次申请到达"}]}
        self.assertEqual(["BUG-1"], source_regressions(before, after)[0]["missing_source_ids"])

    def test_accepts_preserved_historical_source(self):
        before = {"testcases": [{
            "id": "TC-1", "title": "首次申请到达", "radar_source_ids": ["BUG-1"]
        }]}
        after = {"testcases": [{
            "id": "TC-2", "title": "首次申请到达", "historical_source_ids": ["BUG-1"]
        }]}
        self.assertEqual([], source_regressions(before, after))

    def test_flags_renamed_case_without_guessing_its_new_identity(self):
        before = {"testcases": [{
            "id": "TC-1", "title": "旧范围", "radar_source_ids": ["BUG-1"]
        }]}
        after = {"testcases": [{"id": "TC-2", "title": "新范围"}]}
        findings = source_regressions(before, after)
        self.assertEqual("unmatched_title_review_case_rename_or_removal", findings[0]["status"])
        self.assertIsNone(findings[0]["new_id"])


if __name__ == "__main__":
    unittest.main()

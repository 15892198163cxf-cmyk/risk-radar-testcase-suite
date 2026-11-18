#!/usr/bin/env python3

import argparse
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("landmine.py")
SPEC = importlib.util.spec_from_file_location("ziniao_landmine", SCRIPT)
LANDMINE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(LANDMINE)


QUERIES = [
    "账号锁定审批",
    "成员部门角色授权",
    "优化本地端口分配兜底",
    "Passkey 自动二步验证回收站",
]


def capture_bug_search(query, **shared):
    args = argparse.Namespace(
        query=query,
        limit=20,
        min_score=20,
        explain=True,
        no_scenarios=False,
        **shared,
    )
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        LANDMINE.cmd_bug_search(args)
    return output.getvalue()


class RadarSearchFastPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_bug_file = LANDMINE.NORMALIZED_BUGS_FILE
        LANDMINE.NORMALIZED_BUGS_FILE = Path(cls.temp_dir.name) / "normalized_bugs.jsonl"
        row = {
            "id": "7002059071",
            "title": "店铺账号锁定申请审批状态未正确更新",
            "module": "账号管理",
            "category": "线上缺陷/管理系统",
            "keywords": ["账号锁定", "申请审批", "审批权限"],
            "trigger_conditions": ["店铺账号发起锁定申请后执行审批"],
            "failure_symptoms": ["审批状态未正确更新"],
            "expected_result": ["审批状态与操作结果一致"],
            "fix_clues": [],
            "has_detail": True,
            "created_at": "2026-01-01T00:00:00Z",
        }
        LANDMINE.NORMALIZED_BUGS_FILE.write_text(
            json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        cls.shared = {
            "_bug_rows": LANDMINE.load_jsonl(LANDMINE.NORMALIZED_BUGS_FILE),
            "_scenario_items": LANDMINE.load_scenario_index(),
            "_alias_config": LANDMINE.load_alias_config(),
        }

    @classmethod
    def tearDownClass(cls):
        LANDMINE.NORMALIZED_BUGS_FILE = cls.original_bug_file
        cls.temp_dir.cleanup()

    def test_cached_bug_search_is_byte_equivalent(self):
        for query in QUERIES:
            with self.subTest(query=query):
                self.assertEqual(capture_bug_search(query), capture_bug_search(query, **self.shared))

    def test_cached_scoring_is_exact(self):
        for query in QUERIES:
            context = LANDMINE.detect_query_context(query, self.shared["_alias_config"])
            for row in self.shared["_bug_rows"]:
                self.assertEqual(
                    LANDMINE.score_bug_detail(row, query),
                    LANDMINE.score_bug_detail(row, query, context=context),
                )

    def test_batch_deduplicates_equivalent_queries(self):
        args = argparse.Namespace(
            query="账号锁定审批",
            related=["账号锁定审批", " 账号锁定审批 ", "审批权限"],
            recall_limit=12,
            group_limit=3,
            check_limit=5,
            evidence_limit=4,
            bug_limit=8,
            min_score=20,
            no_scenarios=False,
            explain=False,
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            LANDMINE.cmd_radar_search(args)
        rendered = output.getvalue()
        self.assertEqual(2, rendered.count("=== Bug query"))
        self.assertIn("=== Bug query 1/2: 账号锁定审批 ===", rendered)
        self.assertIn("=== Bug query 2/2: 审批权限 ===", rendered)

    def test_compound_chinese_query_preserves_same_feature_account_lock_bug(self):
        query = "店铺账号锁定申请审批"
        self.assertIn("账号锁定", LANDMINE.literal_query_terms(query))
        rendered = capture_bug_search(query, **self.shared)
        self.assertIn("7002059071", rendered)

    def test_account_lock_ranking_is_stable_for_workflow_and_standalone_wording(self):
        workflow_result = capture_bug_search("店铺账号锁定申请审批", **self.shared)
        standalone_result = capture_bug_search("账号锁定审批", **self.shared)
        self.assertIn("7002059071", workflow_result)
        self.assertIn("7002059071", standalone_result)

    def test_feature_alias_query_recalls_sibling_alias_evidence(self):
        row = {
            "id": "CACHE-ALIAS-REGRESSION",
            "title": "下载弹窗无法和客户端的下载设置同步",
            "module": "客户端",
            "has_detail": True,
            "created_at": "2026-01-01T00:00:00Z",
        }
        rendered = capture_bug_search(
            "缓存管理 文件下载路径冲突",
            _bug_rows=[row],
            _scenario_items=[],
            _alias_config=self.shared["_alias_config"],
        )
        self.assertIn("CACHE-ALIAS-REGRESSION", rendered)

    def test_missing_bug_cache_degrades_without_aborting_recall(self):
        current = LANDMINE.NORMALIZED_BUGS_FILE
        LANDMINE.NORMALIZED_BUGS_FILE = Path(self.temp_dir.name) / "missing.jsonl"
        try:
            rendered = capture_bug_search("账号锁定审批")
        finally:
            LANDMINE.NORMALIZED_BUGS_FILE = current
        self.assertIn("Bug detail cache unavailable", rendered)


if __name__ == "__main__":
    unittest.main()

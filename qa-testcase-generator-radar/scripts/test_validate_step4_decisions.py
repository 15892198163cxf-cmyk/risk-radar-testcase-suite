import unittest

from validate_step4_decisions import count_html_images, extract_open_prd_questions, validate


PRD = """## 六、待确认问题
| 编号 | 问题 | 影响 | 状态 / 建议 |
| --- | --- | --- | --- |
| Q1 | ~~谁可审批？~~ | 权限 | **已确认：账号管理权限** |
| Q5 | 登录页判定？ | 分流 | 研发+运维共建规则 |
| Q6 | 获取结果？ | 刷新 | 按现网能力确认 |
| Q7 | 是否改密？ | 范围 | 产品确认 |
| Q9 | 首页是谁看？ | 通知 | 本期已按审批人待处理入口落地 |
## 七、资料
"""


def fixture():
    ids = ["PRD-Q5", "PRD-Q6", "PRD-Q7"] + [f"IMPLICIT-{i}" for i in range(4, 11)]
    candidates = [
        {"id": cid, "source_ref": f"current PRD {cid}", "topic": f"decision {cid}"}
        for cid in ids
    ]
    questions = [
        {
            "id": f"Q{i}",
            "text": f"question {i}",
            "recommended_answer": f"proposed answer {i}",
            "impact": f"expected result {i}",
            "basis": f"source and reasoning {i}",
        }
        for i in range(1, 11)
    ]
    return {
        "source_candidates": candidates,
        "dispositions": [
            {
                "candidate_ids": [cid],
                "status": "ask",
                "reason": "current requirement does not settle this product decision",
                "question_id": f"Q{i}",
            }
            for i, cid in enumerate(ids, 1)
        ],
        "questions": questions,
        "candidate_source_review": {
            family: {"status": "checked", "reason": f"reviewed {family} candidates"}
            for family in ("requirement", "prototype", "knowledge", "radar", "prior_run")
        },
    }


class Step4DecisionGateTests(unittest.TestCase):
    def test_extracts_only_unresolved_prd_questions(self):
        self.assertEqual({"Q5", "Q6", "Q7"}, extract_open_prd_questions(PRD))

    def test_complete_cross_analysis_passes(self):
        self.assertEqual([], validate(PRD, fixture()))

    def test_five_question_shortcut_cannot_discard_other_candidates(self):
        audit = fixture()
        audit["dispositions"] = audit["dispositions"][:5]
        audit["questions"] = audit["questions"][:5]
        errors = validate(PRD, audit)
        self.assertTrue(any("unaccounted candidate: IMPLICIT-6" in item for item in errors))

    def test_open_prd_question_cannot_be_omitted_from_inventory(self):
        audit = fixture()
        audit["source_candidates"] = [
            item for item in audit["source_candidates"] if item["id"] != "PRD-Q7"
        ]
        errors = validate(PRD, audit)
        self.assertIn("open PRD question omitted: Q7", errors)

    def test_non_asked_candidate_requires_current_source_basis(self):
        audit = fixture()
        audit["dispositions"][0] = {
            "candidate_ids": ["PRD-Q5"],
            "status": "settled",
            "reason": "old run answered it",
        }
        audit["questions"] = audit["questions"][1:]
        errors = validate(PRD, audit)
        self.assertTrue(any("settled needs current_source_basis" in item for item in errors))

    def test_missing_prototype_review_is_visible(self):
        audit = fixture()
        del audit["candidate_source_review"]["prototype"]
        errors = validate(PRD, audit)
        self.assertIn("candidate_source_review.prototype needs status", errors)

    def test_html_images_cannot_be_claimed_reviewed_without_inventory(self):
        html = '<h2>F01</h2><img src="data:image/png;base64,AA=="><h2>F09</h2><img src="x.png">'
        self.assertEqual(2, count_html_images(html))
        errors = validate(PRD, fixture(), html)
        self.assertTrue(any("prototype.image_reviews must account" in item for item in errors))

    def test_rule_bearing_html_image_must_link_to_candidate(self):
        html = '<h2>F01</h2><img src="data:image/png;base64,AA=="><img src="x.png">'
        audit = fixture()
        audit["candidate_source_review"]["prototype"]["image_reviews"] = [
            {"index": 1, "kind": "rule", "reason": "The screenshot names a terminal scope", "candidate_ids": ["PRD-Q5"]},
            {"index": 2, "kind": "reference_only", "reason": "Layout example with no additional rule"},
        ]
        self.assertEqual([], validate(PRD, audit, html))
        audit["candidate_source_review"]["prototype"]["image_reviews"][0]["candidate_ids"] = ["missing"]
        self.assertTrue(any("rule needs known candidate_ids" in item for item in validate(PRD, audit, html)))


if __name__ == "__main__":
    unittest.main()

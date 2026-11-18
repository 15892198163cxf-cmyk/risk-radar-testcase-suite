# Step 4 decision coverage gate

Use this only in the radar-assisted Step 4 path. The gate checks that independent requirement and prototype candidates, radar candidates, and any discoverable prior-run candidate questions receive an explicit disposition before the user sees the final clarification list. It does not judge whether the model found every implicit ambiguity; the semantic audit in `SKILL.md` remains mandatory.

The temporary UTF-8 JSON input has these fields:

```json
{
  "source_candidates": [
    {"id": "PRD-Q5", "source_ref": "PRD section 6 Q5", "topic": "login-page classification"},
    {"id": "IMPLICIT-01", "source_ref": "PRD section 3.3.3", "topic": "effective-time boundary"}
  ],
  "dispositions": [
    {"candidate_ids": ["PRD-Q5"], "status": "ask", "reason": "rule remains open", "question_id": "Q1"},
    {"candidate_ids": ["IMPLICIT-01"], "status": "settled", "reason": "current PRD defines this boundary", "current_source_basis": "PRD section 3.3.3 exact rule"}
  ],
  "questions": [
    {"id": "Q1", "text": "How is the login page classified?", "recommended_answer": "Use the stated fallback", "impact": "routing and expected result", "basis": "PRD section 6 Q5 and risk analysis"}
  ],
  "candidate_source_review": {
    "requirement": {"status": "checked", "reason": "read full PRD and identified open decisions"},
    "prototype": {
      "status": "checked",
      "reason": "checked both supplied prototypes",
      "image_reviews": [
        {"index": 1, "kind": "rule", "reason": "image names a supported terminal", "candidate_ids": ["IMPLICIT-01"]},
        {"index": 2, "kind": "reference_only", "reason": "layout reference with no additional rule"}
      ]
    },
    "knowledge": {"status": "not_available", "reason": "no additional knowledge source configured"},
    "radar": {"status": "checked", "reason": "merged canonical radar questions"},
    "prior_run": {"status": "not_available", "reason": "no prior candidate list found"}
  }
}
```

The statuses are `ask`, `settled`, `execution_data`, and `out_of_scope`. `settled` needs `current_source_basis`; `execution_data` needs `execution_prerequisite`. Every source candidate must appear in exactly one disposition. Several candidates may share one displayed question when they are the same product decision. The validator automatically finds open `Q` rows in a Markdown `待确认问题` section and requires IDs such as `PRD-Q5` in `source_candidates`. For PDF or images, pass the complete UTF-8 parsed text; if the original table structure is lost, manually inventory explicit open questions before running the gate.

For an HTML requirement, pass the original `.html` file with `--source-html` in addition to the complete parsed text. Inspect its embedded or linked images before marking `prototype` as checked. Record one `image_reviews` entry per `<img>` in document order, starting at 1. Use `kind: rule` and link known candidate IDs when the image contributes a role, platform, state, copy, or other testable rule; use `kind: reference_only` with a reason when it adds no rule. The gate checks that the image inventory is complete and rule-bearing images link to candidates. It cannot decide whether a classification or the candidate's business interpretation is correct; compare the image with adjacent text yourself. When no images exist, omit `image_reviews`.

Run:

```powershell
python scripts/validate_step4_decisions.py <parsed-requirement.txt-or-md> <temporary-audit.json> [--source-html <original-requirement.html>]
```

Keep the candidate inventory compact and task specific. Do not copy old answers as `settled`; compare them with the current PRD and this run's user answers. Do not make a source family `not_available` merely to avoid checking an available input.

# Landmine Schema

Each line in `data/landmines.jsonl` is one JSON object.

Required fields:

- `id`: stable local identifier.
- `source`: `tester_note`, `feishu_online_bug`, `derived_cluster`, or `feishu_cluster`.
- `domain`: broad area, such as `客户端`, `管理系统`, `移动端`, `店铺内`, `官网`, or `运维后台`.
- `module`: Feishu `所属模块` or tester-provided module.
- `category`: Feishu `缺陷分类`, such as `线上缺陷/管理系统`.
- `scene`: short business scene.
- `risk`: reusable risk statement.
- `must_check`: concrete checks to run before release.
- `keywords`: terms used for recall.
- `evidence`: source titles, work item IDs, or notes.
- `confidence`: `confirmed`, `inferred`, or `seed`.
- `last_seen`: `YYYY-MM-DD` when available.

Recommended fields:

- `evidence_level`: `direct_bug`, `cluster_pattern`, or `qa_inference`.
- `severity`
- `defect_type`
- `priority`
- `status`
- `created_at`
- `avoidance`
- `related_modules`

Rules:

- Store evidence as short references, not full private Bug content.
- Merge repeated Bugs into one higher-level landmine when the test action is the same.
- Keep stale landmines but lower confidence if they have not appeared recently.
- A single Bug may seed a low-confidence landmine, but repeated Bugs should raise confidence.
- In recall answers, direct feature-specific Bugs must be separated from broader cluster patterns and general QA suggestions.

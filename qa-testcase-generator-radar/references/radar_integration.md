# Optional Radar Result Adapter

Use this adapter only when the caller supplies a valid concise `radar_result`
produced directly from the current requirement in the same task, or explicitly
supplies a prior structured result whose `requirement_fingerprint` and
`evidence_snapshot_id` both match the current inputs. A Markdown-only radar or a
result with unclear identity is not a handoff. Without a valid result, keep the
ordinary generator flow, density, testcase fields, review, and export unchanged.

## Input

Accept the small contract owned by `risk-radar-testcase-workflow` at
`schemas/radar-result.schema.json`. If its origin is unclear, rerun the radar for
the current requirement. Do not silently ignore an invalid result or claim radar
coverage from stale output.

Consume selected `risks[].test_points`, not raw Bug rows. Preserve
`evidence_type`, `source_ids`, `why_relevant`, conditional wording, and evidence
boundaries. A historical risk proves that a failure happened before; it does not
automatically define current expected behavior.

Treat the received `radar_result` as the provider's canonical semantic result.
Do not rerank it, substitute different Bug IDs, or create a second radar summary
from another search. If requirement analysis makes one item inapplicable, keep
the original risk identity and record it as excluded with a reason. The final
`radar_impact` must use the same risk IDs and evidence types as this object.

## Apply Once

1. Analyze the requirement normally.
2. Add the radar result to Step 3 knowledge input. Merge its questions with the
   generator's Step 4 questions by product decision and ask each once.
3. Build one coverage plan from the requirement, confirmed decisions, generator
   knowledge, and radar test points. Do not generate a radar-blind core first.
4. Merge a radar point into an existing planned scenario when business object,
   condition, action, and observable result are materially the same. Add only a
   still-uncovered material risk. Do not create one testcase per Bug or inflate
   a concise point into a fixed number of cases.
5. Generate, validate, semantically review, obtain user confirmation, and export
   once through the normal generator path.

During self-review, account for every high- and medium-priority radar test point
as covered, excluded with a reason, or pending clarification. Report aggregate
counts plus the final testcase IDs covering retained risks. Do not create an
obligation map, coverage blueprint, frozen core, workflow state, packet manifest,
or binding report.

For a radar-assisted final suite, add one top-level `radar_impact` object. Keep it
small: summary/status/counts plus one item per retained risk. Each item contains
`risk_id`, `risk_title`, concise `help`, `action` (`雷达复核并强化` or `雷达新增用例`),
`testcase_ids`, `reinforced_testcase_ids`, `added_testcase_ids`, and
`evidence_types`. `testcase_ids` is the union of the two contribution lists.
The same testcase ID must not occur in both contribution classes, including
across different risks. Derive top-level `enhanced_cases` and `added_cases` from
the distinct IDs in those lists; never type those totals independently. The
normal exporter validates the references and recalculates the displayed totals before
turning this object into
the second `雷达增益` worksheet in the same write operation. This is part of the
final suite, not a separate mapping artifact. Do not make the exporter reopen the
radar result or other workflow files.

Use `雷达复核并强化` for requirement-core cases whose coverage was checked or
strengthened by radar input. Reserve `雷达新增用例` for materially new cases that
the requirement-core plan could not absorb. When one risk has both contribution
classes, use `雷达复核并强化 + 雷达新增用例`; do not label every linked case as newly
added. The exporter normalizes the legacy
labels `增强已有用例` and `新增用例` to these reader-facing terms.

Radar-touched cases may carry optional task-local metadata:
`radar_risk_ids`, `radar_source_ids`, and `radar_evidence_types`. These fields
are not ordinary YAML requirements and do not add columns to the `testcases`
worksheet. If `radar_impact` is missing, the exporter may derive a minimal radar
summary from these fields. A normal no-radar suite has neither and still exports
only the `testcases` worksheet.

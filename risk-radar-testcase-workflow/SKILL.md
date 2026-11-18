---
name: risk-radar-testcase-workflow
description: >
  Run an applicable pre-test risk radar for a requirement, then pass its concise
  risk result to isolated qa-testcase-generator-radar and review the final suite
  with qa-testcase-reviewer-radar so historical risks strengthen coverage without
  changing the standalone no-radar skills. Use for combined radar-assisted
  testcase generation, not radar-only or ordinary testcase-review work.
---

# Risk Radar To Testcase Workflow

This skill orchestrates isolated radar-only dependencies. It does not implement
requirement decomposition, testcase writing, review rules, or Excel export itself.
Those belong to `qa-testcase-generator-radar` and
`qa-testcase-reviewer-radar`. Never modify or route the radar-assisted path
through the standalone `qa-testcase-generator` or `qa-testcase-reviewer`; those
are the unchanged no-radar compatibility path.

## Default Flow

1. Give the same requirement artifact to the applicable radar provider. For
   established Ziniao requirements use `ziniao-landmine-map` with its canonical
   production analysis and `presentation_profile=concise`. The presentation
   profile may shorten only visible wording. Within this task, render any radar
   preview and build the generator handoff from one canonical result rather than
   running the provider twice. Independent runs may group or phrase risks
   differently even against the same requirement and evidence snapshot. The radar
   returns one canonical concise result containing relevant
   risks, evidence boundaries, executable test points, and any questions that
   materially affect those test points.
   When revising an existing suite and its prior structured radar result is
   available, compare that baseline with the new canonical result using
   `scripts/validate_radar_consistency.py <prior-radar.json> <canonical-radar.json> --mode regression`
   before handing the radar to the generator. For comparable inputs, a missing
   direct-history source requires source-level review and a corrected radar or
   documented inapplicability; changed related-history sources require semantic
   review. Do not treat independently regrouped risks as a count mismatch.
2. Give the original requirement plus that radar result to
   `qa-testcase-generator-radar`. The generator follows its mode, analysis,
   clarification, generation, self-review, user-confirmation, and export gates.
   It merges useful radar test points into its one coverage plan before writing
   cases, rather than generating a radar-blind suite and remapping it later.
   Before asking the user, require one visible Step 4 cross-analysis of the
   requirement/prototypes and available rule, testcase, defect, related-module,
   and learned-pattern context. Only then merge the radar's questions. The
   radar `questions` array is not the complete clarification list. For each
   material decision candidate, show whether it is asked, already settled by
   the current requirement, an execution-data prerequisite, or out of scope,
   with its source and reason. This is a short section in the normal Step 4
   message, not a new workflow artifact or a second analysis pass. Before
   presenting the question list, run the radar generator's Step 4 decision
   validator against its independent candidate inventory. For HTML requirements,
   pass the original HTML so embedded images must be accounted for; extracted
   text alone does not prove screenshot rules were reviewed. A valid radar handoff
   does not validate clarification completeness. If the validator fails, repair
   the candidate coverage before asking; do not infer that the radar's question
   count is the final question count.

3. After the final candidate suite is written and radar consumption validation
   passes, invoke `qa-testcase-reviewer-radar` with the requirement, canonical
   radar result, candidate suite, the Step 4 decision-candidate dispositions,
   and the current run's user answers. The reviewer must check clarification
   completeness before claiming the suite passes; case structure and radar
   consumption alone cannot prove that missing product decisions were asked.
   Resolve its high or critical findings, rerun the relevant deterministic gates,
   and only then ask the user to confirm the reviewed artifact for export.

That is the complete default workflow. Do not create a separate coverage
blueprint, ordinary-core suite, obligation map, lean state, packet manifest,
binding report, workflow cache, timing envelope, or workflow-specific exporter.
Do not run the generator twice.

## Radar Result Contract

Use [radar-result.schema.json](schemas/radar-result.schema.json) as the small
handoff shape. Produce and consume it in the same task from the same requirement.
An explicitly supplied prior structured result may be reused unchanged only when
its `requirement_fingerprint` and `evidence_snapshot_id` both match the current
inputs. A Markdown-only prior radar is a regression baseline, not a generator
handoff. The result contains only selected risks. Each risk needs:

- a stable `risk_id`, title, priority, and evidence type;
- a short explanation of why it applies to this requirement;
- one or more concise executable `test_points`;
- source IDs when evidence exists, otherwise an empty list.

The `questions` list may be empty; its entries remain unconfirmed until the user answers them.
The radar must not produce full testcases, testcase IDs, coverage matrices, or
generator implementation fields.

The canonical `radar_result` is the single source of truth. If the workflow also
shows a radar preview, render that preview from this exact object; do not ask the
provider again and do not independently summarize another candidate set. The
generator receives this exact object unchanged.

Before giving the result to the generator, validate the canonical file once. If
preview and handoff are represented by two JSON files, the command must compare
those two files; otherwise validate the single file against itself to prove its
shape and record its semantic fingerprint:

`scripts/validate_radar_consistency.py <preview-or-canonical.json> <handoff-or-canonical.json> --mode exact`

Do not proceed on `[INVALID]` or `[MISMATCH]`. This command is local and read-only;
it must not trigger another radar run or create another radar interpretation.

Use strict consistency only for two views of the same canonical run:

`scripts/validate_radar_consistency.py <standalone.json> <workflow.json> --mode exact`

For independently generated results, use `--mode regression`. Different risk
IDs, grouping, order, and wording are allowed. A missing direct-history source is
a regression; changed related evidence and non-historical risks require semantic
review rather than byte or object equality. If requirement fingerprints or
evidence snapshot IDs differ, report the results as incomparable instead of
claiming either parity or regression. Do not promise deterministic equivalence
across independent model runs.

If no provider applies, exit the radar-assisted path, invoke the standalone
generator as a separate no-radar flow, and state that no radar was used. If the
radar has no relevant match, pass a valid `no_direct_match` result to the radar
generator; it still handles the requirement normally.

## Generator Consumption Rules

- Accept the radar result produced from the current requirement in this task, or
  an explicitly supplied structured result whose requirement fingerprint and
  evidence snapshot ID both match. If its origin is unclear, rerun the radar
  instead of guessing or reusing an older result.
- Treat radar test points as prioritized analysis input, not as requirements or
  automatically trusted expected behavior. Preserve evidence labels and
  conditional wording.
- Merge radar questions with the generator's own clarification questions and
  ask each product decision once.
- On a repeated requirement, prior question lists are candidate-discovery input,
  not current-run answers. Re-evaluate each material prior question against the
  current PRD: keep a still-open decision, discard a duplicate or a contradicted
  assumption with a reason, and obtain fresh confirmation when the user asks to
  treat the run as a first request. Do not ask all old questions mechanically.
- During coverage planning, merge a radar test point into an existing scenario
  when it verifies the same object, condition, action, and observable result.
  Add a scenario only when a material risk is still uncovered. This is
  “radar-enhanced, not radar-inflated.”
- Run the radar generator's quality validation, then the isolated radar reviewer,
  user confirmation, and Excel export once. Report how many radar risks/test
  points were covered, excluded, or left pending. Put the same concise accounting
  into the final suite's top-level `radar_impact`; the generator exports it as a
  second `雷达增益` sheet. This remains part of the single final workbook, not a
  separate mapping artifact.
- Within every `radar_impact` item, separate `reinforced_testcase_ids` from
  `added_testcase_ids`; their union is `testcase_ids`. Derive the two top-level
  case counts from distinct IDs, validate that every ID exists, and reject overlap
  between contribution classes. Existing reviewed artifacts without these lists
  remain export-compatible, but newly generated radar suites must include them.
- In user-facing accounting and the `雷达增益` sheet, call merged or strengthened
  requirement-core cases `雷达复核并强化` and reserve `雷达新增用例` for materially
  new cases. If one risk has both, show `雷达复核并强化 + 雷达新增用例`. Do not
  describe every radar-touched core case as newly added.

After the generator writes and reviews the final JSON/YAML, but before asking the
user to confirm export, bind it back to the same canonical radar result:

`scripts/validate_radar_consumption.py <canonical-radar.json> <final-suite.json-or-yaml> --strict-trace`

For a revision of an existing suite, also run
`scripts/audit_suite_revision.py <baseline-suite.json-or-yaml> <final-suite.json-or-yaml>`.
Resolve each reported lost historical source before export: keep an applicable
old source in the case's `historical_source_ids` (never invent a current radar
risk ID), or record the concrete reason it no longer applies in the review.
The script matches stable titles; the reviewer must inspect renamed cases too.

For every new case that shares a functional point with an existing case, the
review must name the closest existing case and the new case's unique condition,
action, or observable result. Merge cases when there is no unique check. Do not
claim semantic deduplication from the structural validator alone. A sequential
end-to-end case may coexist with a focused transition case when its additional
transition or state assertion is explicit.

This local read-only gate verifies canonical risk/test-point counts, risk titles,
evidence types, coverage accounting, and testcase references. Do not repair a
failure by rerunning radar or regenerating the suite automatically; report the
specific mismatch and correct only the broken handoff or accounting. The normal
no-radar generator path does not run this gate.

After the user confirms export, use the generator's confirmed-artifact fast path:
export the already reviewed final JSON/YAML once with `export_excel.py`. Do not
reload or rerun the radar, requirement analysis, generation, review, or handoff;
do not convert JSON to YAML; and do not create a temporary workbook followed by
a second spreadsheet import/export or repeated render pass. The exporter's
in-process structural verification is the default acceptance check. Escalate to
additional workbook tooling only when the exporter fails or the user explicitly
requests custom spreadsheet design.

Never modify the radar provider's evidence store or external systems unless the
user explicitly asks for that separate action.

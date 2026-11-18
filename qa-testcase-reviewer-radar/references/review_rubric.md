# Review Rubric

Use this rubric to review generated QA test cases with stable, evidence-based
criteria instead of generic advice.

## 1. Pick The Right Baseline First

Identify these inputs before scoring the suite:

- Mode: `standard` or `detailed`
- Change type: new generation or incremental update
- Requirement type: config, CRUD, workflow, UI interaction, API behavior, data record
- Review scope: full review, coverage-only review, format-only review, or review-and-fix

Do not apply detailed-mode obligations to standard mode.

Do not judge an incremental update as if it were a full rewrite unless the user
explicitly asks for a full-suite review.

Assume no baseline file is available. Apply
[implicit-golden-signals.md](implicit-golden-signals.md) as the default quality
standard.

## 2. Review Coverage First

Check whether the requirement has a visible path into the case set.

### Requirement coverage

- Map each major FP, business rule, validation rule, state rule, and user-visible
  message to at least one testcase.
- Treat PRD copy, toast text, warnings, and notices as testable behavior when they
  change user experience or business outcome.
- Flag any requirement paragraph that has no testcase anchor.

### Mandatory mapping output

Always build a compact mapping matrix:

- requirement rule
- testcase row(s) or id(s)
- status: covered / missing / uncertain

Do not skip this matrix even when time is limited.

### Config and downstream effect coverage

For config-like requirements, check both sides:

- Write side: config UI, save flow, validation, permission
- Read side: where the config takes effect, is consumed, or changes behavior

Flag the suite if it covers only the write side and ignores the read side.

### Cross-module coverage

If the requirement changes other modules, check whether the linked scenes are
reviewed one by one instead of only by a rough count.

Flag the suite when it says "联动已覆盖" but the affected scenes are not listed.

### Linkage and stop-condition coverage

For workflows with trigger and stop rules, verify both sides:

- trigger conditions
- stop/termination conditions
- expected behavior after stop

If stop conditions are missing, treat as high risk.

### History bug protection

If historical bug cases exist, verify that they are still present and are not:

- removed
- merged into a vague umbrella case
- downgraded to low priority without justification

## 3. Review Granularity And Split Logic

Judge whether the suite splits or merges cases at the correct level.

### Standard mode

Allow merging when multiple values verify the same business rule, for example:

- one field with several equivalent invalid inputs
- one field with several boundary values
- one UI component with several similar close or cancel actions

Flag standard mode only when merging hides a different business rule or a different
expected outcome.

### Detailed mode

Expect explicit splitting for:

- distinct input values that are asserted independently
- separate boundary points such as `N-1`, `N`, and `N+1`
- frontend validation and backend validation
- direct API misuse for write operations when applicable
- state-matrix combinations whose behavior differs
- user-facing copy that must match the PRD text exactly

Flag detailed mode when the suite summarizes with phrases like "分别验证" or
"逐项校验" but only supplies one umbrella case.

## 4. Review Duplicates And Conflicts

Look for different cases that prove the same rule with the same outcome.

Treat the pair as a likely duplicate when all of these are true:

- the business rule under test is the same
- the core precondition is the same
- the expected result is materially the same
- the difference in steps or data does not create a new risk

Do not mark as duplicate when the distinction changes the risk surface, such as:

- frontend vs backend validation
- Windows vs macOS behavior when the requirement differs by platform
- admin vs non-admin permissions
- different initial states that change the result

Also flag conflicts:

- same rule but different priorities without reason
- same scene but contradictory expectations
- same title used for different rules

### Rule contradiction check

Explicitly scan for contradiction between requirement and testcase, including:

- invented constraints not present in requirement
- threshold/window conflicts
- delimiter/format conflicts
- inconsistent rule interpretation across testcase rows

Mark invented or conflicting rules as high or severe depending on impact.

## 5. Review Executability

A good testcase must be runnable by a tester without guessing.

### Step quality

Flag steps that:

- omit the actor, object, or data
- combine multiple unrelated checks in one step
- use placeholders such as "输入合法数据" without examples
- hide API checks behind vague wording such as "调用接口验证"

In detailed mode, count numbered steps across the whole suite. Treat an unusually
high single-step ratio as a mechanical-generation warning, then scan every
single-step case for chained actions such as open/input/submit/refresh/query.
Atomic testcase scope does not imply that a testcase has only one execution step.

### Expected-result quality

Flag expected results that:

- say only "显示正常", "操作成功", or similarly abstract wording
- fail to identify where the result is visible
- do not correspond to the steps
- mix multiple independent assertions without structure

Also enforce action/assertion closure: an expected API status, response body, or
authorization result requires an explicit API request in the steps. A permission
case that checks both UI visibility and direct-API authorization must be split in
detailed mode unless both actions and their separate assertions are explicit and
one indivisible business rule is documented.

### Write-read closure check

For any write operation (create/update/extend/publish/config):

- verify backend-side success behavior
- verify read-side effect (frontend/client/query/data)

If read-side effect is missing, mark high risk.

## 6. Review Schema And Export Readiness

Check whether the suite is ready for archive or Excel export.

### YAML structure

Verify these core expectations when the source is YAML:

- top-level key is `testcases`
- every case has `scene`
- `steps` and `expected` stay readable and aligned
- field naming is stable and consistent

### Business grouping

Flag the suite when it groups by technical layer instead of business scene, for
example:

- frontend validation
- backend validation
- database validation

Prefer business-scene grouping and place technical distinctions inside the case.

### Excel-specific risks

If the source is Excel, watch for merged-cell loss:

- blank titles or preconditions that should have inherited merged values
- rows that appear empty only because Excel stored the value in the first merged cell

### OpenClaw exported Excel quick path

If the workbook matches this pattern:

- one sheet named `testcases`
- six headers: `业务场景`, `用例标题`, `前置条件`, `测试步骤`, `预期结果`, `优先级`
- no merged cells

then treat it as a flattened export and check:

- no blank required cells
- scene grouping is still coherent
- priority distribution is reasonable
- titles are specific and not duplicated
- steps and expected results remain executable after export

## 7. Turn Observations Into Severity

Use this mapping consistently:

- 严重: missing core path, false pass risk, major regression hole, or invalid schema
- 高: important business path missing, detailed split missing, history bug weakened
- 中: duplicate/priority/granularity issue with moderate execution risk
- 低: wording, naming, or presentation issue

## 8. End With A Defensible Verdict

Use one of these outcomes:

- `通过`: no material risk found; residual risks are minor
- `通过但需修复`: usable suite, but the listed issues should be fixed before archive or execution
- `不通过`: major coverage, granularity, regression, or schema problems make the suite unreliable

## 9. No-Baseline Mode (Default)

When no historical golden file is available:

- use PRD plus generated testcase artifacts as the source of truth
- enforce implicit golden signals on structure, assertions, and executability
- report findings with the same severity model and evidence standard

Do not lower quality expectations just because no baseline workbook was provided.

## 10. Evidence discipline

For 严重/高 findings, include:

- requirement-side evidence
- testcase-side evidence
- actionable fix

If any part is missing, downgrade to `待确认问题`.

## 11. Integrated Radar Provenance

When workflow artifacts exist, do not trust a reported `VALID` or duplicate count
alone. Inspect whether the ordinary core was frozen before radar mapping and was
built without radar handoff/obligation inputs. Verify that coverage-key data is a
real business condition rather than title/ID/random uniqueness. Recompute likely
duplicates from preconditions, actions, and observable results; an umbrella radar
case that repeats focused core variants is not a valid net addition.

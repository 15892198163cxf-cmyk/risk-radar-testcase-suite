---
name: qa-testcase-reviewer-radar
description: >
  Workflow-private review of radar-assisted testcase suites produced by
  qa-testcase-generator-radar. Check requirement coverage, radar consumption,
  scenario quality, traceability, and export readiness. Use only when explicitly
  invoked by risk-radar-testcase-workflow; ordinary testcase review must use
  qa-testcase-reviewer.
---

# QA 雷达增强用例评审器

This is the isolated reviewer used by `risk-radar-testcase-workflow`. Do not
route ordinary testcase reviews here; use standalone `qa-testcase-reviewer` for
the no-radar path.

## Overview

Perform a second-pass QA review on already-generated test cases before archiving,
Excel export, or execution.

Prefer critique and evidence first. Rewrite cases only when the user explicitly
asks to fix them after the review.

## Prefer The Review Model

If the runtime allows model selection, prefer `gemini-3.1-pro-preview`.

If the runtime cannot pin the model, continue with the available model and state
that the review was not run on the preferred model.

In OpenClaw, keep the prompt focused on review rather than re-generation.

## Gather The Minimum Inputs

Collect as many of these artifacts as possible before judging the suite:

- Requirement source: PRD, Markdown, PDF, screenshots, or pasted text
- Generated cases: YAML, Excel, Markdown, or pasted output
- Generation mode: standard or detailed
- Existing module context: testcase library, history bugs, learned patterns
- For a workflow-generated radar suite: the Step 4 decision-candidate
  disposition table, displayed clarification questions, and current-run user
  answers. Read them from this task's conversation when no separate artifact
  exists; do not require a new state file.

If the missing input changes the verdict, ask a short blocking question before
giving the final conclusion.

## Run The Review Workflow

### 1. Confirm the assignment

Distinguish these two tasks early:

- `review only`: output findings and verdict, do not rewrite
- `review and fix`: output findings first, then patch the cases

Judge the suite against the selected mode. Do not fail standard mode for missing
detailed-mode-only requirements.

### 2. Normalize the artifacts

- Review YAML, Markdown, and pasted text directly.
- Preserve merged-cell semantics when the input is Excel; do not treat merged
  scene, title, or precondition cells as empty rows.
- Parse or OCR PDFs and images before judging them.

For OpenClaw-exported Excel files, first assume a flat export pattern:

- workbook usually contains one sheet named `testcases`
- headers usually are `业务场景 / 用例标题 / 前置条件 / 测试步骤 / 预期结果 / 优先级`
- rows are often already flattened, so merged-cell recovery may not be needed

If the file matches this pattern, review it directly as an exported case table.

### 3. Build the rubric

Read [references/review_rubric.md](references/review_rubric.md).
Always read
[references/implicit-golden-signals.md](references/implicit-golden-signals.md)
to apply high-quality review standards even when no benchmark file is provided.
Always read
[references/mandatory-review-gates.md](references/mandatory-review-gates.md)
and execute all mandatory gates before giving a verdict.

If the sibling generator skill exists, also read only the files needed for the
current review from:

- `../qa-testcase-generator-radar/references/self_review_checklist.md`
- `../qa-testcase-generator-radar/references/output_format.md`
- `../qa-testcase-generator-radar/references/detailed_mode_rules.md`
- `../qa-testcase-generator-radar/references/coverage_strategies.md`

If `../qa-knowledge/` exists, read the module's testcase library, history bug
records, and learned patterns when they affect the verdict.

### 4. Review in passes

Review in this order so findings stay concrete:

1. Requirement and FP coverage
   For a workflow-generated radar suite, first compare the source's explicit
   open questions and material implicit ambiguities with the Step 4 candidate
   dispositions. Confirm every `ask` decision was displayed and answered in
   this run, or that the user explicitly accepted its displayed default. Check
   that `current requirement settled` cites the current source, `execution-data
   prerequisite` does not hide a product decision, and radar questions were
   merged only after independent requirement/context analysis. Prior-run answers
   are not confirmation when the user requested a fresh run. If the table or
   answers are unavailable, do not issue `通过`; report the unverified gate.
2. Scene granularity and split correctness
3. Duplicate cases, overlaps, and priority quality
4. Step and expected-result executability
5. YAML or Excel format and archive readiness

For detailed suites, perform a whole-suite numbered-step scan before sampling.
Check mechanical single-step collapse, action/assertion closure, and UI/API
permission separation. When integrated radar artifacts exist, also audit ordinary
core provenance and semantic-fingerprint integrity; never accept a prior
validator's `VALID` result as sufficient evidence.

### 4.1 Mandatory output blocks

The review output must include these blocks:

1. Requirement-to-testcase mapping matrix
2. Rule contradiction check
3. Linkage/state-transition check
4. Write-read closure check

If any block is missing, do not return `通过`.

### 5. Output findings first

Use [references/review_report_template.md](references/review_report_template.md).

默认输出语言为中文，除非用户明确要求英文。

Order findings by severity:

- 严重
- 高
- 中
- 低

For every finding, point to the exact scene, title, row, or testcase id when
possible. Explain why it is a problem, what evidence supports it, and what
specific fix is needed.
For 严重/高 findings, evidence must include both requirement-side and testcase-side
citations. If evidence is incomplete, move it to `待确认问题`.

### 6. Give a verdict

Return exactly one verdict:

- `通过`
- `通过但需修复`
- `不通过`

Summarize the biggest risks in 3-5 short lines.

If the user asked for fixes, revise the suite only after the review section.

## Enforce The Hard-Fail Checks

Treat these as hard failures unless the user explicitly narrows the review scope:

- Miss core business scenes from the requirement
- Claim clarification completeness from the radar question count, deterministic
  case validation, or a previous run's accepted answers without checking the
  current requirement's decision candidates and this run's confirmations
- Miss detailed-mode-only frontend and backend separation where required
- Cover config write scenarios but miss downstream read or effect scenarios
- Delete, merge away, or downgrade history-bug cases
- Duplicate the same business rule across multiple cases without a useful distinction
- Write steps that are too abstract to execute
- Write expected results that are not observable or verifiable
- Mechanically collapse most detailed-mode cases into one numbered step while
  chaining multiple executable actions
- Assert API status/body/authorization without an explicit API request in steps
- Use testcase titles, IDs, random values, or hashes as coverage data to defeat
  semantic duplicate detection
- Build the claimed ordinary core from radar obligations or radar-only context
- Break archive or export schema expectations such as `testcases`, `scene`,
  `steps`, or `expected`

## Apply Severity Consistently

- 严重: break release confidence or create false coverage
- 高: miss an important scenario or design the case set incorrectly
- 中: have clear granularity, structure, or priority problems with moderate risk
- 低: have wording, consistency, or polish issues that do not change core coverage

## Respect The Review Boundaries

- Do not invent business rules; mark unknown logic as an open question.
- Do not silently upgrade standard mode into detailed mode.
- Do not give generic advice such as "补充边界测试"; name the exact missing
  boundary, rule, or scene.
- Do not output only praise; if the suite is strong, still show what was checked
  and what residual risk remains.
- Do not use role-play language; keep the report professional and factual.

## Review OpenClaw Excel Efficiently

When the input is an OpenClaw output file such as `*_vN.xlsx`:

1. Identify the sheet, headers, row count, and whether merged cells exist.
2. Sample the first rows and the last rows to understand scene spread.
3. Count cases by `业务场景` and by `优先级`.
4. Check for blank mandatory fields and duplicate titles.
5. Then perform semantic review on high-risk scenes first:
   - core P0 scenes
   - exception and fallback scenes
   - interface validation scenes
   - security scenes

## Use These Prompt Shapes

- `用 $qa-testcase-reviewer-radar 评审雷达工作流生成的 YAML 用例，按严重程度列问题，不要直接改。`
- `用 $qa-testcase-reviewer-radar 按详细模式对照 PRD 和 radar_result 评审，并只修复高/严重问题。`
- `用 $qa-testcase-reviewer-radar 检查雷达增强 Excel 是否漏测、重复或追溯错误。`

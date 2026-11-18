# Implicit Golden Signals (No Baseline File Required)

Use these signals as default quality standards when no historical golden testcase
file is available.

These signals are distilled from high-quality testcase sets and are intended to
be applied generically across modules.

## 1. Structure Signals

A strong testcase set should show:

- clear business-scene grouping
- specific, non-generic testcase titles
- explicit preconditions with runnable context
- stable priority assignment and rationale
- minimal blank or placeholder fields

## 2. Assertion Signals

A strong testcase should prefer measurable assertions over vague wording.

Prefer:

- explicit thresholds (length, count, size, time, code)
- explicit route patterns and parameter forms
- explicit expected status/error behavior
- explicit data persistence or sync checks

Avoid:

- "正常", "无异常", "符合预期" without observable criteria
- ambiguous fallback wording like "按实现处理"

## 3. Rule-Fidelity Signals

A strong suite should fully cover key rule families:

- input validation rules
- ranking/sorting/display rules
- route and URL rules
- permission and role boundaries
- security controls (injection, upload, replay, authorization)
- frontend/backend parity checks

## 4. Executability Signals

A strong suite should be executable by another tester without tribal knowledge.

Check that:

- test data is concrete, not abstract placeholders
- steps are atomic and ordered
- expected results map clearly to steps
- pass/fail can be judged from observable output

## 5. Coverage Depth Signals

A strong suite should not only cover CRUD happy paths.

Look for:

- negative and boundary paths
- state-transition combinations
- cross-module linkage scenarios
- downstream effect checks after config changes

## 6. Regression-Readiness Signals

A strong suite should support repeated execution and release gating.

Look for:

- stable IDs/naming patterns where needed
- priority mix with meaningful P0/P1 split
- compact but sufficient duplicate-control
- safety-net checks for historical fragile areas

## 7. Optional Scoring

Use lightweight scoring if helpful:

- Structure quality: 0-5
- Assertion quality: 0-5
- Rule fidelity: 0-5
- Executability: 0-5
- Regression readiness: 0-5

`>=20` usually indicates strong production-ready testcase quality.

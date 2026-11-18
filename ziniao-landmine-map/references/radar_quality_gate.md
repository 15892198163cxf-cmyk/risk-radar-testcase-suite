# Radar Quality Gate

Use this review before finalizing a detailed PRD radar, a model-expansion radar, a client runtime-chain radar, or a response whose quality is being compared with an earlier version. Judge semantic usefulness, not exact wording, heading count, or a fixed number of items.

Read `risk_model.md` to select change profiles and applicable risk dimensions. For disputed, benchmarked, or high-impact requirements, build the version 5 internal JSON described in `radar_plan_schema.md` and run `radar-check` before rendering the final answer.

## Review Sequence

0. **Route parity**
   - Was one canonical radar result used for both standalone rendering and workflow handoff?
   - Given the same requirement and evidence snapshot, are risk IDs, priorities, evidence/source IDs, executable test points, boundaries, and material questions identical after order normalization?
   - Does a presentation profile change only wording density, not evidence depth or selected content?
   - If multiple JSON representations exist, run the workflow consistency validator; any semantic mismatch is a hard failure before testcase generation.

1. **Object correctness**
   - Is the business object and surface correct?
   - Are similarly named concepts separated, especially Ziniao login accounts versus store/platform accounts?
   - If evidence crosses a surface or module, is the shared model, component, or failure mode explained?

2. **Evidence availability**
   - Were exact/synonym detail search and scenario search both considered?
   - Are direct Bugs retained when they explain a current failure mode?
   - Are adjacent Bugs demoted and labeled rather than silently removed when still useful?
   - Are weak keyword-only matches omitted?
   - If OpenViking is configured, is remote status recorded as `queried`, `no_match`, `unavailable`, `not_configured`, or `skipped` rather than left ambiguous?
   - Were accepted rules checked before ordinary testcase atoms, and was every used remote URI read rather than cited from a search abstract?
   - Did remote evidence add a missing risk dimension or correct a business boundary instead of merely increasing the answer length?
   - Does `historical_testcase_review` show the actual testcase queries, every evaluated candidate's decision and reason, and the risks influenced by selected candidates? If retrieval was skipped or unavailable, is the limitation explicit rather than silently treated as no match?

3. **PRD-named impact inventory**
   - Before selecting final risks, extract the pages, entries, shared-component consumers, fields, states, logs, notifications, and visible copy that the current PRD explicitly names.
   - After drafting, compare that inventory with the radar. A named impact may be grouped with related entries, but the wording must still let the tester identify every affected route. A module-only summary is insufficient when the routes require separate regression.
   - Put lower-priority named impacts under `扩展回归面` or group them into one identifiable item. Internal coverage is mandatory; one visible bullet per minor copy change is not.
   - This comparison uses the current requirement as its source. Do not carry one PRD's entry list into unrelated authorization or permission requests.
   - Extract explicit invariants and negative rules, including `only`, `must not`, `no automatic`, `no migration`, `does not restore`, `permanent`, and `immediate`. High- and medium-priority constraints must map to a visible risk or an explicit exclusion.

4. **Conflict and scope audit**
   - Compare body rules, tables, acceptance criteria, screenshots, and interaction notes for contradictions. Do not choose a winner without evidence.
   - A risk that depends on an unresolved conflict must use conditional wording and name the competing interpretations under `需求疑点`.
   - For client resources or global settings, identify owner, sharing model, lifecycle boundary, and consumers before asserting one-resource-per-instance, per-workbench independence, or release timing.
   - If scope is unknown, test the stable outcome: correct mapping, no cross-impact, and release at the actual owner's lifecycle boundary. Keep architecture-specific expectations conditional.

5. **Requirement-model coverage**
   - Derive risk dimensions from what changed, not from a generic checklist.
   - Confirm that each high-value dimension is either represented or deliberately excluded with a reason.
   - Mark each generic dimension as applicable or not applicable with a reason. Only applicable dimensions enter the radar.
   - Do not use fixed item quotas. One strong point can cover a dimension; several duplicate Bugs do not create broader coverage.

6. **Practical mapping**
   - For each retained Bug, state the historical failure and why it can recur now.
   - Convert it into an observable focus, not a full testcase.
   - Include the trigger, identity, state, data shape, entry, or environment that makes the risk executable.
   - Build the applicability bridge before calling evidence direct or strong related: current object/shared dependency, historical failure mechanism, and current trigger.
   - If the shared dependency or current trigger is not established, move the point to a concrete conditional regression instead of presenting it as confirmed.
   - In version 4 or 5 plans, encode every strong-related bridge structurally. A same-object flag is only context; it does not replace confirmed shared data, component, runtime, lifecycle, or execution-point evidence.
   - Group direct and strong related Bugs by failure mechanism. Preserve each material trigger combination and assertion through a coverage obligation; do not require one visible point per Bug.

7. **Evidence boundary**
   - Direct history, same-model history, shared-component regression, and ordinary QA inference must remain distinguishable.
   - Do not claim an affected surface or caller chain that the PRD, diff, product model, or Bug evidence does not establish.
   - Record whether evidence is current, cross-version, legacy, or unknown. V5-only, old-kernel-only, old-UI, or rebuilt-module evidence must be downgraded unless its root cause still applies.
   - Separate recurrence-risk authority from correct-behavior authority. A Bug proves historical failure; an applicability-matched accepted rule defines business behavior; a testcase supplies a regression hint; none of these proves current implementation by itself.
   - For remote knowledge, compare product, surface, scope, version, date, valid/not-valid ranges, and applies/not-applicable ranges. Unknown applicability must remain conditional; not-matched evidence must be excluded.
   - Enforce the remote budget: no more than five narrow queries, eight reads, and five visible remote additions unless the user requested a broad audit. Zero or one remote addition is valid; never add filler to meet a count.

   Apply the remote evidence admission gate before ranking:

   - **Independence:** current same-requirement testcases are coverage-audit material, not independent history. They cannot support recurrence claims or be counted as a quality gain.
   - **Scope:** a source supports only its explicit product, surface, object types, roles, versions, and conditions. Split mixed-object risks when only part of the claim is supported.
   - **Claim strength:** compare every risk sentence with the source's actual assertion. A historical testcase cannot be expanded into a stronger algorithm, log requirement, failure-handling rule, or compatibility promise.
   - **Admission:** only evidence recorded as `selected` may support a risk. Keep same-requirement or useful-but-insufficient material as `scope_audit_only`; reject mismatched material.

8. **Assertion separation**
   - Split a mixed risk into internal assertions before rendering whenever its sentences rely on different authority: online Bug, requirement, accepted business rule, historical testcase, or QA inference.
   - Keep each assertion inside its own source boundary. A history-backed masking assertion does not prove every secret type leaked; a page-loading symptom does not prove a resource/cache cause; a lifecycle inference does not become an upgrade-history claim.
   - Keep a useful supplemental check as an inference or requirement assertion instead of deleting it merely because the Bug does not prove it.
   - Require a separate condition and condition render anchor on the assertion whose dependency, object, trigger, or product expectation is unresolved; the final draft must preserve both the risk and the condition.
   - Render assertions compactly under one risk when readable, but preserve distinct evidence labels and certainty. Assertion separation must not turn the radar into a testcase table.

9. **Reader-facing compression and priority**
   - Keep internal dimensions, assertions, and evidence mappings in the plan; do not automatically turn each one into a separate Markdown section.
   - Give each failure mechanism one primary visible home. Logs, notifications, compatibility effects, or display consequences may stay under that risk when they are part of the same trigger and observable failure.
   - The same Bug may legitimately support different facts. Merge by failure mechanism and repeated assertion, not by Bug ID alone.
   - Do not set a fixed item or line quota. Preserve every distinct high-value risk, but remove repeated setup, evidence descriptions, and conclusions that add no new action.
   - Use P0/P1 only when the requirement, team convention, or an explicit impact/probability rule supports those labels. Otherwise order the risks or group them as `首轮必测` and `扩展回归`.
   - Review `obligation_split_across_sections` and `risk_priority_saturation` warnings from `radar-check --draft`. A warning is a prompt for semantic review, not an automatic failure or instruction to shorten the radar.

### Mandatory Final Claim-Boundary Audit

After the draft is written, audit every source-backed sentence against the selected source's `claim_boundary`. For each sentence, answer four questions: does the source establish this object, this trigger, this observed result, and every concrete technical noun used in the sentence? If any answer is no, split the unsupported part into a separately labeled requirement or QA-inference assertion, make it conditional when its applicability is unknown, or remove it when it adds no testing value.

Keep conditions at their smallest valid scope. Do not place an unconditional compatibility check and an implementation-dependent equivalence check under one shared condition. Typical failures this audit must reject include: a rule about entry visibility being expanded into proven interface enforcement; a display-truncation Bug being expanded into an internal-ID failure; a generic credential-safety inference naming an unconfirmed secret or storage implementation; and ordinary path compatibility being made conditional on a separate normalization algorithm.

This is a semantic review, not a new validator guarantee. `radar-check` cannot determine whether a paraphrase exceeds the meaning of the source text, so a structural PASS never replaces this audit.

10. **Regression comparison**
   - When an earlier answer exists, compare by risk dimensions, not length.
   - A newer answer may reclassify or remove an incorrect, obsolete, duplicated, or out-of-scope point, but the internal plan must record the reason.
   - It must not lose a valuable dimension without an explicit reason.
   - It must not lose a high- or medium-priority failure-mechanism obligation, material trigger combination, or observable assertion without an explicit reason.
   - Business knowledge should improve routing and wording. If it only makes the answer shorter, review for over-pruning.
   - Do not report decimal quality scores or use character-count reduction as proof of improvement. Report concrete passes, regressions, exclusions, and unresolved judgments instead.

## Generic Change-Profile Review

Use profiles from `risk_model.md` rather than requirement-specific hard-coded rules:

- `ui_copy`: normally requires display and i18n review only. Add other dimensions only when the changed control triggers behavior.
- `list_query`: review query semantics and displayed results; add permission, state, or export only when named or dependency-backed.
- `permission_authorization`: review persistence, scope, display, old query assumptions, and downstream records when the underlying authorization model changes.
- `lifecycle`: review state transitions, failure/cancel/retry/repeat operations, historical data, and downstream records.
- `client_runtime`: review the plausible dependency chain, isolation, release/recovery, and upgrade compatibility; keep unproven callers conditional.
- `shared_component`: inventory every named consumer and map it to a regression route without calling every consumer direct Bug evidence.
- `security_sensitive`: review masking, secrets, protected operations, interface authorization, and runtime invalidation.

These are applicability prompts, not fixed output templates. If a dimension is not triggered, mark it not applicable with a reason and omit it from the user-facing radar.

## Release Regression Gate

Treat concrete requirements as evaluation fixtures, not production instructions. A skill change is acceptable only when:

- known regression fixtures keep all valid high-value dimensions;
- known regression fixtures keep all valid high- and medium-priority coverage obligations;
- removed prior items have explicit exclusion reasons;
- cross-type forward fixtures do not become generic checklists;
- no direct/adjacent or current/legacy evidence boundary regresses;
- the final draft contains every high- and medium-priority risk from its validated plan;
- the final draft contains every high- and medium-priority assertion from a version 4 or 5 plan;
- repeated generation does not intermittently fail a hard gate.

Run known fixtures and at least one requirement that did not motivate the current rule change. Exact wording is not a quality signal; impact coverage, evidence applicability, and observability are.

## Fail Conditions

Review again when any of these is true:

- The business object is correct but the answer contains only one or two risks for a broad model or chain change.
- A direct Bug was removed only because its title or Feishu module label is imperfect, despite matching steps and failure mode.
- Adjacent evidence is presented as direct history, or useful adjacent evidence disappears without explanation.
- A PRD explicitly names affected entries, but the final radar compresses them into a module-level label that cannot be mapped back to each regression route.
- The response is longer but adds no new risk dimension.
- The response resembles complete testcases instead of a pre-test risk radar.
- A newer version is less executable than the previous version and the lost coverage cannot be justified.
- A direct or strong related historical mechanism is retained, but its material identity, permission, state, data-shape, concurrency, or save-path trigger disappears during rendering.
- A chain or shared-component Bug is presented as applicable without naming the dependency and current trigger, or remains unconditional while that connection is unknown.
- A dimension is included without an applicability reason, causing a generic checklist.
- A prior risk disappears without either equivalent coverage or an exclusion reason.
- A legacy-only Bug is presented as current direct evidence without a demonstrated shared root cause.
- A PRD conflict is listed at the end but one side is asserted as mandatory earlier in the radar.
- A global/client-owned resource is described as one-per-workbench or released per store without ownership evidence.
- An explicit negative rule, exception, no-migration rule, retention rule, or non-goal disappears from the radar despite material risk.
- A recall benchmark pass is described as proof that generated radar quality or non-overfitting has been established.
- A subjective decimal score or shorter character count is presented as proof that radar quality improved.
- A search abstract is cited as remote evidence without reading the underlying `viking://` item.
- The same Feishu Bug appears once from the local archive and again from OpenViking as two separate risks.
- A remote timeout or authorization failure is described as “no matching history”, or a successful no-match is described as service failure.
- An `ACCEPTED_L1` rule is presented as proof that current code implements the behavior, or a historical testcase is presented as an online Bug.
- A testcase generated from the current requirement is cited as independent history, used to support a recurrence risk, or counted as evidence that the new radar improved.
- A remote source about one object type, directory, role, or runtime is generalized to other objects without separate evidence or conditional wording.
- A historical testcase is rewritten into a stronger expectation than it actually asserts, such as a specific allocation algorithm, retry count, log granularity, cleanup rule, or compatibility behavior.
- One rendered sentence combines a source-backed historical fact and an unsupported cause, object expansion, secret type, caller, or recovery promise without a separately labeled assertion.
- An inference assertion carries Bug or testcase sources to make it look historical, or a historical assertion has no source.
- An assertion cites an evidence role that does not match its basis, such as an accepted business rule presented as historical failure or a requirement assertion carrying a Bug source.
- A conditional assertion is rendered without the phrase that communicates when it applies.
- Two materially different assertions reuse one render anchor, allowing one phrase to satisfy multiple claims during validation.
- One coverage obligation is rendered as multiple top-level risks only because it supports multiple internal dimensions, even though the trigger and observable assertion are the same.
- Most visible risks use the same P0/P1 label without an explicit prioritization basis, leaving the tester no useful execution order.

## Evaluation Claim Boundary

`radar-check` validates plan structure, mappings, conditionality, and draft anchors. `radar-eval` validates generic validator mutations and Bug recall fixtures. Neither command proves that every forward requirement was rendered into a good radar or that the skill cannot overfit. Report their result narrowly and keep an independent semantic review for final quality claims.

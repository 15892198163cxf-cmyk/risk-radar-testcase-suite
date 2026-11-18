# Structured Radar Plan

Use a structured plan before rendering a detailed or disputed radar. The plan is internal working data; the user-facing answer remains concise prose.

## Abbreviated JSON Shape

This excerpt shows the version 5 fields. A real plan still assesses all risk dimensions and includes every referenced impact and risk. Version 5 keeps the version 4 assertion-level provenance and adds a historical-testcase retrieval and decision audit so a radar cannot pass merely because Bug recall and inference succeeded.

```json
{
  "version": 5,
  "requirement": {
    "title": "...",
    "object": "...",
    "surfaces": ["客户端"],
    "change_profiles": ["client_runtime"],
    "legacy_in_scope": false
  },
  "impact_inventory": [
    {"id": "I1", "label": "named entry or behavior", "priority": "high", "source_status": "confirmed"},
    {"id": "I2", "label": "disputed behavior", "priority": "high", "source_status": "conflicted"}
  ],
  "requirement_constraints": [
    {"id": "C1", "label": "does not restore historical bindings", "kind": "negative", "priority": "high"}
  ],
  "requirement_conflicts": [
    {
      "id": "Q1",
      "label": "whether manual permanent deletion is supported",
      "reason": "body and acceptance criteria disagree",
      "impact_ids": ["I2"],
      "risk_ids": ["R2"]
    }
  ],
  "scope_models": [
    {
      "id": "S1",
      "subject": "local port service",
      "owner": "unknown",
      "sharing": "unknown across workbenches",
      "lifecycle": "unknown release boundary",
      "status": "unknown",
      "reason": "no implementation diff",
      "risk_ids": ["R3"]
    }
  ],
  "dimension_applicability": [
    {"dimension": "runtime_chain", "status": "applicable", "reason": "changed capability supports store startup"},
    {"dimension": "state_transition", "status": "applicable", "reason": "the disputed rule changes a state transition"},
    {"dimension": "permission_scope", "status": "not_applicable", "reason": "requirement does not change permission behavior"}
  ],
  "remote_knowledge": {
    "status": "queried",
    "reason": "accepted rules and historical testcases may clarify this authorization change",
    "queries": ["账号授权 成员 部门 角色"],
    "read_refs": [
      "viking://resources/.../accepted-rule.handoff.md",
      "viking://resources/.../testcase-atoms.jsonl"
    ]
  },
  "historical_testcase_review": {
    "status": "queried",
    "reason": "historical account-authorization cases were evaluated as radar input",
    "queries": ["账号授权 成员 部门 角色 历史用例"],
    "candidates": [
      {
        "candidate_id": "TC-ZINIAO-EXAMPLE",
        "source_ref": "viking://resources/.../testcase-atoms.jsonl",
        "title": "historical authorization save case",
        "decision": "selected",
        "reason": "same authorization persistence model and observable save result",
        "evidence_id": "E3",
        "risk_ids": ["R1"]
      }
    ]
  },
  "evidence": [
    {
      "id": "E1",
      "source_type": "feishu_bug",
      "evidence_role": "risk_history",
      "source_ref": "feishu://bug/123456",
      "bug_id": "123456",
      "title": "historical failure",
      "level": "strong_related",
      "same_object": true,
      "same_entry_or_chain": true,
      "version_scope": "current",
      "source_updated_at": "2026-08-01",
      "applicability_status": "matched",
      "applicability_reason": "why the historical failure can recur",
      "bridge": {
        "kind": "shared_data_model",
        "status": "confirmed",
        "description": "the old and current flows persist the same authorization relation",
        "current_trigger": "saving the expanded authorization object reaches that persistence model"
      }
    },
    {
      "id": "E2",
      "source_type": "openviking_accepted",
      "evidence_role": "behavior_rule",
      "source_ref": "viking://resources/.../accepted-rule.handoff.md",
      "title": "accepted authorization boundary",
      "level": "direct",
      "same_object": true,
      "same_entry_or_chain": true,
      "version_scope": "current",
      "source_updated_at": "2026-07-30",
      "applicability_status": "matched",
      "applicability_reason": "product, surface, scope, and role match the current requirement",
      "provenance_relation": "independent_history",
      "admission_status": "selected",
      "claim_boundary": "defines the accepted member authorization boundary only; it does not cover departments or roles"
    },
    {
      "id": "E3",
      "source_type": "openviking_testcase",
      "evidence_role": "regression_hint",
      "source_ref": "viking://resources/.../testcase-atoms.jsonl",
      "title": "historical authorization save case",
      "level": "strong_related",
      "same_object": true,
      "same_entry_or_chain": true,
      "version_scope": "current",
      "source_updated_at": "2026-07-15",
      "applicability_status": "matched",
      "applicability_reason": "the historical testcase exercises the same authorization persistence model",
      "bridge": {
        "kind": "shared_data_model",
        "status": "confirmed",
        "description": "both flows persist the same authorization relation",
        "current_trigger": "saving the expanded authorization object reaches that relation"
      },
      "provenance_relation": "independent_history",
      "admission_status": "selected",
      "claim_boundary": "supports only the recorded authorization save and preservation assertion"
    }
  ],
  "coverage_obligations": [
    {
      "id": "O1",
      "failure_mechanism": "an unrelated save path overwrites an existing authorization relation",
      "trigger_conditions": ["existing mixed authorization", "actor lacks authorization-edit permission", "save an unrelated field"],
      "required_assertion": "the authorization relation and authorization audit record remain unchanged",
      "priority": "high",
      "source_ids": ["E1", "E3"]
    }
  ],
  "risks": [
    {
      "id": "R1",
      "title": "short risk title",
      "render_anchor": "unique phrase expected in the final draft",
      "dimension": "runtime_chain",
      "priority": "high",
      "basis": "historical",
      "certainty": "confirmed",
      "source_ids": ["E1", "E3"],
      "coverage_obligation_ids": ["O1"],
      "constraint_ids": ["C1"],
      "impact_ids": ["I1"],
      "observable_focus": "trigger and visible failure to watch",
      "assertions": [
        {
          "id": "A1",
          "text": "an unrelated save previously overwrote an existing authorization relation",
          "basis": "historical",
          "certainty": "confirmed",
          "source_ids": ["E1"],
          "render_anchor": "unrelated save must preserve authorization"
        },
        {
          "id": "A1-TC",
          "text": "the historical testcase adds the authorization preservation regression hint",
          "basis": "historical_testcase",
          "certainty": "confirmed",
          "source_ids": ["E3"],
          "render_anchor": "historical authorization preservation case"
        },
        {
          "id": "A2",
          "text": "mixed authorization objects should also remain unchanged",
          "basis": "inference",
          "certainty": "confirmed",
          "source_ids": [],
          "render_anchor": "mixed objects remain unchanged"
        }
      ]
    },
    {
      "id": "R2",
      "title": "disputed behavior",
      "render_anchor": "conditional disputed behavior",
      "dimension": "state_transition",
      "priority": "high",
      "basis": "requirement",
      "certainty": "conditional",
      "condition": "only if the product owner confirms the acceptance-criteria interpretation",
      "source_ids": [],
      "coverage_obligation_ids": [],
      "constraint_ids": [],
      "impact_ids": ["I2"],
      "observable_focus": "state outcome under the confirmed interpretation",
      "assertions": [
        {
          "id": "A3",
          "text": "validate permanent deletion only after the disputed behavior is confirmed",
          "basis": "requirement",
          "certainty": "conditional",
          "condition": "only if the product owner confirms the acceptance-criteria interpretation",
          "condition_render_anchor": "after the permanent-deletion rule is confirmed",
          "source_ids": [],
          "render_anchor": "confirm permanent deletion before testing it"
        }
      ]
    },
    {
      "id": "R3",
      "title": "resource sharing and release",
      "render_anchor": "owner lifecycle boundary",
      "dimension": "runtime_chain",
      "priority": "high",
      "basis": "inference",
      "certainty": "conditional",
      "condition": "verify uniqueness and release timing against the actual resource owner and sharing model",
      "source_ids": [],
      "coverage_obligation_ids": [],
      "constraint_ids": [],
      "impact_ids": ["I1"],
      "observable_focus": "correct mapping, no cross-impact, and release at the owner lifecycle boundary",
      "assertions": [
        {
          "id": "A4",
          "text": "resource mapping and release depend on the actual owner and sharing model",
          "basis": "inference",
          "certainty": "conditional",
          "condition": "verify against the actual resource owner and sharing model",
          "condition_render_anchor": "only after the resource owner is confirmed",
          "source_ids": [],
          "render_anchor": "release at the actual owner boundary"
        }
      ]
    }
  ],
  "exclusions": [
    {"id": "X1", "target_id": "old-risk-or-impact-id", "reason": "wrong object, obsolete, duplicate, or intentionally grouped"}
  ],
  "questions": ["unresolved product expectation"]
}
```

## Validation Rules

- IDs must be unique within each collection.
- Every impact item must be covered by at least one risk or have an explicit exclusion reason.
- Version 2, 3, and 4 impact items declare `source_status`: `confirmed`, `conflicted`, or `unknown`.
- Version 3, 4, and 5 plans include `remote_knowledge` with `status`, `reason`, `queries`, and `read_refs`. Query count must not exceed five and read references must not exceed eight.
- Version 3, 4, and 5 evidence declares `source_type`, `evidence_role`, `source_ref`, `source_updated_at`, and `applicability_status`.
- Version 5 plans include `historical_testcase_review` with `status`, `reason`, `queries`, and `candidates`. `queried` requires at least one candidate; use `no_match` when a completed search produced none. `unavailable`, `not_configured`, and `skipped` require an explanation and cannot carry candidates.
- Every historical testcase candidate records a stable candidate ID, `viking://` source reference, recognizable title, `selected`/`scope_audit_only`/`rejected` decision, and concrete reason. A selected candidate also records its evidence ID and at least one risk ID it influenced; the evidence must be a selected `regression_hint` and the named risk must contain that evidence ID.
- In version 3 and 4, `applicability_reason` is the semantic bridge: identify the current object or shared dependency, the historical failure mechanism, and the current trigger. It may state that a dependency or trigger is unknown, but the linked risk must then be conditional.
- Every OpenViking item also declares `provenance_relation` (`independent_history`, `same_requirement`, or `unknown`), `admission_status` (`selected`, `scope_audit_only`, or `rejected`), and a non-empty `claim_boundary`.
- OpenViking evidence must use a `viking://` source reference. A local Feishu Bug must retain its `bug_id`.
- Only `admission_status=selected` OpenViking evidence may support a risk, and its `source_ref` must be present in `remote_knowledge.read_refs`. Same-requirement material cannot be selected or referenced by a risk; it is limited to scope auditing.
- Unknown provenance can support only a conditional risk. A not-matched remote item cannot be selected.
- `applicability_status=not_matched` evidence cannot support a risk. `applicability_status=unknown` may support only a conditional risk with a concrete condition.
- `behavior_rule` evidence defines expected behavior only within its matched scope; it is not historical Bug proof. `regression_hint` evidence is a supplemental historical testcase, not proof that a failure occurred online.
- `claim_boundary` is the maximum claim the source can support. Object types, diagnostic detail, algorithms, retry/recovery behavior, and compatibility rules outside that boundary must use another source or remain labeled inference/conditional.
- Version 3 and 4 plans include `coverage_obligations`. Group equivalent direct or strong related history by failure mechanism instead of creating one obligation per Bug. Each obligation declares `failure_mechanism`, non-empty `trigger_conditions`, `required_assertion`, `priority`, and `source_ids`.
- Every obligation source must exist and use `level=direct` or `level=strong_related`. A high- or medium-priority obligation must map through a risk's `coverage_obligation_ids` or have an explicit exclusion.
- A historical or historical-testcase risk that uses direct or strong related evidence must map at least one coverage obligation. The obligation is about preserving a mechanism, trigger, and assertion; it does not require one visible bullet per Bug.
- Extract high- and medium-priority explicit invariants, negative requirements, and exclusions into `requirement_constraints`; each must map to a risk through `constraint_ids` or to an exclusion.
- Record unresolved PRD contradictions in `requirement_conflicts`. Every linked risk must use `certainty=conditional` and include a concrete `condition`.
- For `client_runtime` plans, add at least one `scope_models` entry covering resource owner, sharing model, lifecycle, and evidence status. Risks linked to an unknown scope model must be conditional.
- Every applicable dimension must have at least one risk; non-applicable dimensions need a reason.
- Every risk needs a concrete observable focus and at least one impact mapping.
- Historical risks must reference evidence. Inference risks must not pretend to have Bug evidence.
- Every version 4 or 5 risk contains one or more `assertions`. Each assertion has a risk-local unique `id`, non-empty `text`, valid `basis`, valid `certainty`, `source_ids`, and a unique `render_anchor` for high- or medium-priority risks.
- Historical, cluster, business-rule, and historical-testcase assertions require evidence. Evidence roles must match assertion basis: historical uses `risk_history` or `tester_experience`, historical testcase uses `regression_hint`, business rule uses `behavior_rule`, and cluster uses `cluster_signal`. Requirement and inference assertions cannot carry evidence. Assertion sources must also be listed on their parent risk; every parent-risk source must support at least one assertion.
- The parent risk's `basis` must occur among its assertion bases. This keeps the risk-level summary compatible with the assertion-level authority while allowing a mixed risk to retain a primary basis.
- A conditional assertion requires its own concrete `condition` and `condition_render_anchor`. When a draft is supplied, both its risk assertion anchor and condition anchor must appear. Do not rely only on the parent risk's condition when one assertion is confirmed and another is conditional.
- A conditional parent risk must contain at least one conditional assertion; otherwise its condition has no claim-level path into the final draft.
- Historical and historical-testcase assertions backed by direct or strong-related evidence must be covered by the parent risk's failure-mechanism obligations.
- Assertion render anchors must be unique across the plan. When a draft is supplied, every high- and medium-priority assertion anchor must be present. Risk anchors remain for backward-compatible risk-level retention; assertion anchors verify that mixed claim bases were not collapsed during rendering.
- Direct evidence requires both `same_object=true` and `same_entry_or_chain=true`.
- In version 4 or 5, every `strong_related` item requires a structured `bridge` with a valid `kind`, `status=confirmed`, a concrete `description`, and a concrete `current_trigger`. Valid kinds are `same_execution_point`, `shared_data_model`, `shared_component`, `shared_runtime_dependency`, and `shared_lifecycle`.
- `same_object=true` or keyword/module proximity is not enough for `strong_related`. The bridge must identify the actual shared dependency or execution mechanism and how the current delta reaches it. `same_execution_point` additionally requires `same_entry_or_chain=true`.
- `strong_related` evidence requires `applicability_status=matched`. If the shared implementation, owner, caller, or trigger is unknown, classify the item as `adjacent` with `applicability_status=unknown` and keep the linked assertion conditional; do not create a direct/strong-related coverage obligation from it.
- Legacy evidence cannot be direct unless `legacy_in_scope=true`.
- Every high- or medium-priority risk needs a `render_anchor`. When a draft is supplied, all anchors must be present.
- Version 2, 3, and 4 risks declare `certainty=confirmed` or `conditional`; conditional risks require a condition. Risks covering conflicted or unknown impacts must be conditional.
- Evidence strength and risk priority are independent. Do not infer priority from `level`, and do not relabel a high-priority requirement or security risk as direct history merely because it is important.
- A prior risk may disappear only when `exclusions` records a concrete reason; wrong or obsolete content is allowed to be removed.
- With a draft, `radar-check` warns when one coverage obligation is mapped to risk anchors found under different Markdown sections. Internal risks may cover different dimensions, but the rendered radar should normally give the shared failure mechanism one primary visible home.
- With four or more risks, `radar-check` warns when at least 80 percent share one priority. This is a review signal only: do not demote real risks mechanically, and do not impose a fixed item count.

Versions 1-4 remain readable for old artifacts. Use version 5 for new detailed, disputed, PRD-based, client-runtime, or OpenViking-assisted work. Version 5 provenance and historical-testcase review fields are internal controls, not a requirement to print more bullets or pass historical testcase rows to the testcase generator.

## Commands

Validate a plan:

```powershell
py scripts/landmine.py radar-check plan.json
```

Validate both the plan and rendered Markdown:

```powershell
py scripts/landmine.py radar-check plan.json --draft radar.md
```

Use `--benchmark <case-id>` only during regression evaluation. Benchmark data must not alter production risk selection.

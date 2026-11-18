# Generic Radar Risk Model

Use this model for detailed requirements, disputed radar quality, or any change that spans a data model or runtime chain. It is a decision framework, not a checklist to print.

## Requirement Delta First

Describe what changed before selecting risks:

- business object and surface;
- existing behavior versus new behavior;
- named pages, entries, fields, actions, states, and shared consumers;
- runtime boundaries such as management system, client shell, and store-inside environment;
- affected identities, permissions, historical data, and versions.

Also extract explicit constraints, especially counterintuitive rules expressed as `only`, `must not`, `does not`, `never`, `permanently`, `immediately`, `no migration`, `no automatic cleanup`, or `does not restore`. These rules are often more valuable than ordinary happy-path behavior and must not disappear during compression.

If two requirement sections disagree, record a conflict before selecting risks. Do not silently choose one side. Any risk that depends on the disputed rule must be conditional until the product owner resolves it.

Do not activate a risk dimension merely because it exists in this file. A dimension is applicable only when the requirement delta, historical evidence, shared dependency, or current product model gives a concrete reason.

## Change Profiles

A requirement may use more than one profile.

- `ui_copy`: visible copy, layout, button placement, dialog wording, or interaction-only changes.
- `list_query`: list fields, search, filters, sort, pagination, exports, or query semantics.
- `permission_authorization`: roles, authorization objects, visible scope, data scope, or interface authorization.
- `lifecycle`: create, update, purchase, renew, enable, disable, delete, restore, expire, replace, or migrate state.
- `client_runtime`: local service, ports, kernel, resource package, cache, path, startup, upgrade, process, or multi-workbench behavior.
- `shared_component`: a selector, dialog, interface, data model, or component reused by multiple entries.
- `migration_compatibility`: old data, old configuration, upgrade, version conversion, renamed fields, or rebuilt modules.
- `security_sensitive`: credentials, Passkey, passwords, cookies, verification secrets, phone numbers, or other protected data.

Profiles route the analysis; they do not mandate fixed output sections or item counts.

Multiple affected entries do not by themselves prove a `shared_component` profile. Record the entries as affected surfaces first. Use `shared_component` only when the PRD, diff, runtime evidence, or accepted knowledge confirms reuse of a selector, dialog, interface, data model, or implementation dependency. If reuse is plausible but unconfirmed, mark the related impact `unknown` and keep consumer-regression wording conditional.

Each profile has only its semantic minimum: copy changes require display/i18n, list changes require display/query semantics, permission changes require permission scope, lifecycle changes require state transitions, client runtime changes require runtime-chain analysis, shared components require consumer coverage, migrations require compatibility, and sensitive data requires security/privacy. All other dimensions remain requirement-dependent.

## Scope And Ownership Before Isolation Claims

For `client_runtime`, global settings, local services, ports, processes, caches, paths, or shared components, identify these before writing isolation or release checks:

- who owns the resource or configuration: client process, workbench, store process, kernel, user, or enterprise;
- whether it is shared or one-per-instance;
- when its lifecycle begins and ends;
- which consumers read it and how they receive updates.

If any of these are unknown, keep the risk but phrase it conditionally. Do not infer that every workbench needs a different port, that every workbench has independent path settings, or that closing one store must release a client-owned service. The stable test objective is correct mapping, no cross-impact, and release at the actual owner's lifecycle boundary.

## Risk Dimensions

For each dimension, mark it internally as `applicable` or `not_applicable` and give a reason.

- `data_persistence`: save, overwrite, accidental clearing, mapping, migration, and historical data.
- `display_consistency`: list, detail, dialog, hover, copy, empty state, and source labeling.
- `query_semantics`: search, filter, sort, pagination, count, export, and old query assumptions.
- `permission_scope`: entry, button, data range, interface authorization, over-permission, and under-permission.
- `state_transition`: success, failure, cancel, retry, repeat, expiry, restore, and idempotency.
- `runtime_chain`: upstream/downstream calls, startup, client-kernel communication, store-inside effect, and stale callers.
- `isolation_concurrency`: multiple workbenches, stores, users, windows, concurrent operations, and cross-object contamination.
- `resource_release_recovery`: ports, processes, files, cache, rollback, restart, and recovery after failure.
- `shared_consumers`: every named page, entry, interface, or workflow that reuses the changed component or model.
- `downstream_records`: operation logs, notifications, audit records, statistics, and derived views.
- `compatibility`: historical data/configuration, upgrade, old version, kernel difference, and rebuilt surfaces.
- `security_privacy`: masking, secret exposure, protected operations, verification, and least privilege.
- `i18n_copy`: visible Chinese/English copy, dynamic parameters, truncation, wrapping, and layout.

## Applicability Examples

- A copy-only change normally activates `display_consistency` and `i18n_copy`; it does not activate permission or lifecycle checks without another trigger.
- A new list filter normally activates `query_semantics` and may activate `permission_scope` or `display_consistency` when the filtered data is permission-bound or shown elsewhere.
- An authorization-object expansion normally activates persistence, display, query, permission, downstream records, and compatibility because the underlying data model changed.
- A local-port or kernel change normally activates runtime chain, isolation/concurrency, release/recovery, and compatibility because it supports multiple runtime nodes.
- A recycle-bin or credential-state change normally activates state transition, persistence, permission, downstream records, compatibility, and security/privacy.

## Evidence Applicability

Rank evidence using facts, not matching keywords:

- `direct`: same business object and same entry, state transition, interface, or execution-chain failure point.
- `strong_related`: same object/model/dependency and a failure mode that can plausibly recur through the current change.
- `same_model`: another entry using the same hierarchy, permission, lifecycle, query, or shared-component model.
- `adjacent`: useful failure pattern on a different object or surface; keep it lower priority and explain the transfer.
- `inference`: QA reasoning without local Bug evidence.

Evidence strength does not remove requirement uncertainty. A real historical Bug can support a risk pattern while the current resource ownership, sharing model, or expected behavior remains unknown. In that case keep the evidence label and make the current check conditional.

For every retained source, write an applicability bridge in `applicability_reason` that covers three questions as far as the evidence allows:

1. Which current object, shared component, data model, lifecycle, or runtime dependency connects the source?
2. What historical failure mechanism is being transferred?
3. Which part of the current delta can trigger that mechanism?

This is a graded decision. Same-object and same-entry evidence normally supports `direct`; a demonstrated shared dependency can support `strong_related` across entries or modules. When the trigger or dependency is unconfirmed, keep the risk conditional and name the missing fact. Keyword similarity or broad module proximity without a mechanism bridge is not applicable evidence.

Keep evidence relationship and business priority independent. Evidence answers how strongly history supports recurrence. Priority answers how severe and likely the current failure would be. A security or data-loss risk can be high priority when derived from an explicit requirement even without a direct historical Bug; label its basis honestly.

Also record version applicability:

- `current`: current surface or current implementation family.
- `cross_version`: root cause remains plausible across versions.
- `legacy`: old UI, V5-only, old-kernel-only, or rebuilt implementation.
- `unknown`: applicability cannot be confirmed.

Legacy evidence must not be labeled direct unless the current requirement explicitly includes that legacy version or the root cause is demonstrated to remain shared.

## Lossless Compression

Compress only after the impact inventory, applicable dimensions, and evidence mapping are complete.

Before rendering, group direct and strong related history into failure-mechanism coverage obligations. Each obligation records:

- the historical failure mechanism;
- only the trigger combinations that materially expose it;
- the observable assertion that the radar must retain;
- the supporting sources and the risk that renders it.

Several Bugs with the same mechanism should share one obligation. Do not create one visible item per Bug. Conversely, do not merge two Bugs when doing so removes a distinct identity, permission, state, data-shape, concurrency, or save-path trigger that changes what the tester must exercise.

Apply the same ownership rule across output sections. Each failure mode, trigger condition, and assertion should have one primary visible home. Refer back briefly only when necessary; do not repeat disabled/deleted-object handling under both hierarchy selection and state fallback, or repeat the same compatibility save check under history and inference without adding a distinct reason or assertion.

Allowed:

- merge duplicate Bugs that describe the same failure mode;
- group low-risk named UI changes under one extension item;
- omit a previous item when it is wrong, obsolete, duplicated, or outside scope, with an internal exclusion reason.

Not allowed:

- remove a distinct high-value risk dimension merely to shorten the answer;
- remove a high- or medium-priority coverage obligation, material trigger combination, or required assertion without an explicit exclusion reason;
- hide a PRD-named entry that needs an identifiable regression route;
- turn adjacent evidence into direct history to make the radar look stronger;
- expand every dimension into a full testcase checklist.
- drop explicit negative requirements or exception rules because they do not resemble a normal user action;
- turn a disputed requirement or unknown architecture assumption into an unconditional expected result.

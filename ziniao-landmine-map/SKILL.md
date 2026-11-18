---
name: ziniao-landmine-map
description: Recall and maintain a Ziniao pre-test risk radar from the governed OpenViking mirror of Feishu online defects, a validated local cache, tester experience, and optional OpenViking business-rule or historical-testcase evidence before testing client, admin, mobile, store, kernel, account, device, cloud-number, security, or related modules.
---

# Ziniao Landmine Map

## Non-Negotiable Product Objective

Before testing starts, use Ziniao historical online Bugs and tester experience to warn which risks in the current change are most likely to recur and most likely to be missed.

This skill is a pre-test risk radar, not a testcase generator. It must output concise, executable test points derived from the retained risks. Each important risk should tell the tester what condition, operation, identity, state, or data shape to exercise and what failure or result to observe. By default it stops at risk, evidence, why the risk applies now, concise test points, and minimum data needed to execute them. Do not expand into comprehensive scenario coverage, testcase IDs, exhaustive preconditions, step-by-step procedures, expected-result blocks, or coverage matrices. If the user explicitly asks for full testcases, treat that as a separate testcase-generation task rather than stretching the radar output.

Use this skill when the user is preparing to test a Ziniao feature, asks for historical pitfalls, wants to turn Feishu online Bugs into reusable testing risks, or says to record a new Ziniao testing pitfall.

The goal is not to repeat every Bug and not to teach testing from scratch. Convert historical online Bugs and tester experience into high-signal pre-test reminders: what is most likely to recur in this requirement, what is easiest to miss, the trigger conditions, likely failure modes, and concrete checks.

## Data Sources

Primary fast-recall data lives in `data/landmines.jsonl`. The governed historical Bug dataset is distributed through `viking://resources/ziniao-online-bugs-governed`; `data/normalized_bugs.jsonl` is its validated local mirror and remains the deterministic input to the existing recall, scenario, cluster, alias, and ranking logic.

Generated Feishu cluster landmines live in `data/feishu_cluster_landmines.jsonl`. Query aliases live in `data/query_aliases.yaml`; ranking rules live in `data/recall_rules.yaml`.

Scenario-level recall lives in `data/scenario_index.json`. It is generated from normalized Feishu Bugs and should be checked before relying on individual Bug rows. Candidate scenarios and the human review report live in `data/scenario_candidates.json` and `data/scenario_candidates.md`; only high-confidence seeded scenarios are promoted into the formal index.

Feishu view imports are rolling current-window snapshots. Keep them separate from the long-term evidence archive:

- `data/feishu_raw/view_Khmxw2UDR_normalized.json`: the latest current-window view snapshot.
- `data/feishu_raw/view_ZZdtquUvR_normalized.json`: the broader historical online-Bug snapshot used for archive backfill.
- `data/feishu_raw/feishu_bug_details.jsonl`: detail cache for Bugs still visible in the current-window view.
- `data/feishu_raw/all_bug_details.jsonl`: long-term detail archive. Monthly refreshes append or update this file and must not delete Bugs that left the current rolling window.
- `data/normalized_bugs.jsonl`: searchable normalized detail evidence built from the long-term archive and mirrored to/from OpenViking.

Each normalized Bug is stored once and carries `view_memberships` plus `source_view_ids`:

- `current_182d`: present in the rolling 182-day view `Khmxw2UDR`;
- `historical_view`: present in the broader view `ZZdtquUvR`;
- long-term archive: every row in `normalized_bugs.jsonl`, including rows in neither current view.

Use the detail layer for narrow feature questions when the landmine cache has no strong hit. Rank freshness from `created_at`, not from view membership: Bugs inside the latest 182 calendar days receive the current-window boost, Bugs aged 182-364 days receive a smaller history boost, and Bugs aged 365 days or more are lightly demoted. `window_status` remains a compatibility field derived from `current_182d`; it is not a time bucket. Older direct evidence remains eligible and should still outrank recent keyword-only evidence.

Feishu online defects are an upstream source, not the live dependency for every recall. When importing or refreshing from Feishu, use read-only queries unless the user explicitly asks for a write-back and confirms the exact write action.

OpenViking has two distinct roles. The governed online-Bug dataset is the team distribution source and is synchronized into the local normalized cache before recall. Accepted business rules and historical testcases remain optional remote evidence queried on demand through the installed `openviking_knowledge_remote` MCP server. The Studio Playground URL is a human interface and must not be used as the integration endpoint. Keep the remote API credential in `OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY`, never in skill files, plans, or radar output.

Use OpenViking without changing the existing evidence semantics:

- the governed OpenViking Bug archive and its local mirror are one source, not two independent sources; never double-count them;
- Feishu Bugs and tester notes prove historical recurrence risk;
- OpenViking `ACCEPTED_L1` clarifies intended business behavior and scope when applicability matches;
- 2026 formal testcase atoms provide current historical regression hints; 2025 testcases are lower-weight historical context;
- `CANDIDATE_L1`, temporary testcases, normalized atoms with unknown expectations, and `NEEDS_CONFIRMATION` records cannot define the current expected behavior;
- radar search still runs against the validated local mirror so aliases, scenario routing, clustering, age weighting, and regression fixtures remain deterministic. If the remote preflight is unavailable or invalid, continue with the last validated local cache and disclose the fallback briefly.

Read `references/openviking_bug_dataset.md` when publishing, verifying, troubleshooting, or changing this synchronization contract.

Known Feishu source for the current seed:

- Project key: `3zobdi`
- View: `https://project.feishu.cn/3zobdi/workObjectView/zxqx/Khmxw2UDR?scope=workspaces&node=30406156`
- Historical backfill view: `https://project.feishu.cn/3zobdi/workObjectView/zxqx/ZZdtquUvR`
- Work item type: `执行缺陷`
- Defect category field: `field_24ef5b` (`缺陷分类`)
- Module field: `field_8a92da` (`所属模块`)
- Created time fields: `start_time`, `field_c65ba1`
- Useful detail fields: `field_318642` (`备注`), `field_45f401` (`修复方案`), `field_1a4393` (`严重程度`), `field_9ad8d4` (`缺陷类型`), `field_2849cf` (`优先级`)

For Feishu data, prefer the view API over hand-written MQL when reproducing the user's screenshot filters, because tree child categories such as `线上缺陷/管理系统` and `线上缺陷/V6客户端` are represented as child values.

## Ziniao Product Model

Read `references/ziniao_domain_model.md` before making supplemental testing inferences that cross `客户端`, `管理系统`, or `店铺内` boundaries.

Read `references/ziniao_business_context.md` when a request depends on module ownership, PRD scope routing, Bug evidence strength, or an easily confused business concept that is not fully covered in the domain model. This reference distills two external knowledge-base answers; use it as routing support, not as stronger evidence than user-confirmed rules, real Feishu Bugs, or current PRD text.

Read `references/risk_model.md` for detailed PRDs, disputed quality, model expansions, or runtime-chain changes. It provides generic change profiles, applicability-based risk dimensions, evidence version handling, and lossless compression. Do not turn its dimensions into a fixed checklist.

In short: 紫鸟是一个客户端；管理系统是客户端里的在线页面；店铺内是由独立浏览器内核创建的隔离浏览器环境. Do not describe these as ordinary independent terminals. For example, after a 管理系统 purchase, the default visibility check is whether 管理系统 can see the purchased state, not whether the 客户端 or 店铺内 also sees it. Only add 客户端 shell or 店铺内 checks when the feature explicitly affects client resources, launch behavior, local cache, browser environment, plugins, account startup, or store runtime state.

For any request that says `账号`, first resolve which account concept is meant before searching or citing Bugs:

- `账号中心`, `账号设置`, `紫鸟账号`, `登录账号`, `成员账号`, `手机号`, `绑定管理`, or `安全中心` means the Ziniao login/member account. Prioritize 紫鸟账号 evidence and exclude 店铺账号 evidence unless the requirement explicitly mentions store/platform accounts.
- `账号列表`, `账号管理`, `店铺账号`, `平台账号`, `电商平台账号`, `编辑账号`, `授权成员`, `托管账密`, `附加账号`, or `主账号` means a store/platform account. Prioritize 店铺账号 evidence.
- If both meanings are plausible, state the ambiguity and use nearby terms to decide. Do not cite `账号列表/编辑账号/授权成员` Bugs for an `账号中心/账号设置` request just because both contain `账号` or `授权`.

Before adding supplemental runtime checks, apply these product boundaries from the domain model: opening a store/account browser enters an environment-safety and network-validation flow, but do not assume every device type uses the same IP-check interface or that proxy, cookie restoration, local ports, plugins, access policy, and supervision are unconditional steps; local ports are implementation dependencies only when the change or evidence connects them to opening stores or client-to-kernel communication; 云号 does not imply opening-store checks unless explicitly connected to store runtime; `事中监管/添加监管账号/告警方案` is the supervision family, while `访问策略/会员安全策略` is the access-policy family. Treat store-operation supervision separately from management-system login, operation, and permission logs. Visible page copy requires English translation.

## Change Type

The same landmine data supports two testing situations, but the response wording and inference stance must differ.

- **旧功能改动:** Treat the request as regression-risk recall. Prioritize direct historical Bugs for the same module, field, entry, and flow. Say that these are places that have broken before and may regress after this change. Example wording: `这是旧功能改动，优先看历史复发风险`.
- **新功能新增:** Treat the request as impact-surface analysis. The new feature may not have same-name historical Bugs, so search the containing module, interaction type, data type, permission model, list/filter behavior, and adjacent flows. Clearly mark which items are historical evidence and which are design inference. Example wording: `这是新功能新增，历史上不一定有同名 Bug，以下按同模块/同交互推导`.

If the user does not say which type it is, infer conservatively from wording:

- `改动`, `修改`, `调整`, `优化`, `新增字段`, `编辑`, `原功能`, or an existing entry/field usually means 旧功能改动.
- `新增功能`, `新入口`, `新页面`, `新能力`, or a feature with no prior entry usually means 新功能新增.
- If uncertain, state the assumption briefly instead of asking unless the distinction materially changes the answer.

## Recall Priority

The radar's first job is to warn about high-probability regressions and high-probability missed checks. Product knowledge is a routing and correction layer, not a reason to suppress useful risks.

Use this sequence. Do not compress or prune before the coverage obligations are built:

1. **Resolve the object.** Identify account type, surface, module, runtime, business object, and change model.
2. **Recall broadly within that object.** Collect same-feature Bugs, same-model Bugs, shared-component Bugs, and plausible adjacent failure modes. Keep the candidate pool broad enough to expose likely omissions.
3. **Correct with business knowledge.** Remove truly mismatched objects. Demote useful cross-surface or cross-module evidence to adjacent evidence instead of deleting it when the same data model, component, or failure mode still applies.
4. **Build an applicability bridge.** For each retained source, explain the current object or shared dependency, the historical failure mechanism, and how the present change can trigger it. Missing implementation or ownership facts make the risk conditional; keyword similarity alone rejects it.
5. **Audit risk dimensions.** For the recognized change model, check whether the candidate set covers the relevant save, display, filter, hierarchy, permission, state, compatibility, log, notification, shared-component, or runtime-chain dimensions.
6. **Create failure-mechanism obligations.** Group direct and strong related history by failure mechanism, then preserve the material trigger combination and observable assertion that must survive rendering. Multiple Bugs may map to one obligation; do not create one output item per Bug.
7. **Split mixed claims.** When one visible risk combines historical fact, requirement behavior, business rule, testcase hint, or QA inference, record them as separate assertions before rendering. A source-backed fact stops at its claim boundary; an additional useful check remains, but keeps its own basis and certainty.
8. **Rank and label independently.** Keep evidence relationship (`direct`, `strong_related`, `same_model`, `adjacent`) separate from business priority (`high`, `medium`, `low`). A high-impact requirement-derived risk can be P0/high without pretending to be direct history.
9. **Compress last.** Remove duplication and weak items only after the important dimensions, coverage obligations, and assertions are represented. Conciseness must not come from dropping a high-value trigger, assertion, or risk dimension.

When invoked by `risk-radar-testcase-workflow`, build one canonical radar result
for the current task. Render any standalone-style preview and the generator
handoff from that exact object; do not run recall twice or independently rewrite
the visible radar and handoff. The workflow may request
`presentation_profile=concise`, but that profile controls only wording density
and visible sections within this run. Independent model runs may group, order, or
phrase risks differently even for the same requirement and evidence snapshot;
compare those runs by retained failure mechanisms, direct/strong-related history,
material test points, boundaries, and exclusions rather than exact risk IDs or
wording. Do not promise deterministic equivalence across independent runs.

Use the same applicable risk-model and quality-gate reasoning in both routes.
The workflow does not need to persist a V5 plan unless a detailed audit or
dispute requires it, but skipping a persisted plan must not weaken selection or
drop a direct/strong-related failure mechanism. Performance optimization may
reuse loaded data and batch queries; it may not use a shallower evidence path.

 For a multi-feature PRD, list each changed function or entry before recall and
 include a narrow query for every distinct failure mechanism (for example,
 login authorization arrival and company-information completion are different
 from generic login-state queries). Before finalizing even a concise handoff,
 reconcile every direct or strong-related local candidate with the canonical
 risks: selected with its source ID, or excluded with a concrete applicability
 reason. A high-ranked candidate must not disappear only because the visible
 radar is short. If a prior structured radar for the same requirement and Bug
 snapshot is available, run the workflow's regression comparison before using
 the new result; resolve missing direct history and review changed related
 history before generation.

For a standalone detailed, high-impact, benchmarked, or disputed radar, build an internal structured plan using `references/radar_plan_schema.md`. Assess every generic risk dimension as applicable or not applicable with a reason, map every named impact to a risk or an exclusion, and validate the plan before rendering. This plan is internal; do not expose JSON to the user unless requested.

Use structured plan version 5 for new detailed or disputed work. It keeps version 4 assertion-level provenance and adds a mandatory `historical_testcase_review` audit. The audit records whether historical testcase retrieval was queried, produced no match, was unavailable/not configured, or was deliberately skipped; every candidate records its selected/scope-audit/rejected decision and reason, and every selected candidate names the risk it influenced. Versions 1-4 remain readable for existing artifacts. A conflict-dependent or architecture-dependent risk must remain conditional; do not assert one side of a PRD conflict or assume resource ownership, per-workbench independence, or release timing.

## Applicability And Retention Gate

Apply this gate to local Bugs, tester experience, historical testcases, and remote evidence before ranking:

- **Direct:** same business object and same entry, transition, interface, or execution failure point; the current delta can reach the historical mechanism.
- **Strong related:** a shared data model, component, runtime dependency, or lifecycle mechanism connects the source to the current change. Name that connection explicitly.
- **Conditional adjacent:** the mechanism is useful but the changed implementation, resource owner, caller, or shared dependency is not confirmed. Keep it under a concrete `if the implementation touches/reuses...` condition instead of a main confirmed claim.
- **Reject:** only keywords, broad module proximity, or a different object with no shared mechanism connects the source.

For version 4 or 5 plans, encode every `strong_related` connection in the structured `bridge` object defined by `references/radar_plan_schema.md`. `same_object=true` alone never establishes strong relation. If the bridge cannot be marked `confirmed` with a concrete current trigger, downgrade the evidence to conditional `adjacent` or reject it before building coverage obligations.

The bridge is graded, not a requirement that every source match the same object, mechanism, and entry simultaneously. Cross-module evidence is valid when a real shared dependency or failure mechanism is established. The validator checks that mappings and conditions exist; the model must make the semantic judgment.

For every direct or strong related historical mechanism retained in a detailed plan, record one coverage obligation containing the failure mechanism, material trigger conditions, required observable assertion, and supporting source IDs. Deduplicate equivalent Bugs into one obligation. Preserve identity, permission, state, data shape, concurrency, or save-path combinations only when they materially create the historical failure. Every high- or medium-priority obligation must map to a rendered risk or an explicit exclusion reason.

For every version 4 or 5 risk, add one or more `assertions`. Each assertion has its own `basis`, `source_ids`, `certainty`, optional `condition`, and unique `render_anchor`; a conditional assertion also has `condition_render_anchor`. Historical, business-rule, testcase, requirement, and inference assertions may share one user-facing risk only after this split. Match assertion basis to evidence role: historical to Bug/tester history, historical testcase to regression hints, business rule to accepted rule evidence, and cluster to cluster evidence. Requirement and inference assertions do not inherit evidence IDs. Source-backed assertions must not silently expand to a different object, cause, secret type, caller, or recovery promise. Keep these assertion records internal and render them as concise test points rather than exposing the plan.

## OpenViking Remote Knowledge

This section governs accepted business rules and historical testcases. The governed online-Bug archive uses the cache preflight in `references/openviking_bug_dataset.md`; do not run a second semantic Bug search after the mirror is current.

Call the read-only `mcp__openviking_knowledge_remote__*` tools directly from this skill. Do not invoke the plugin's standalone `business-memory-answerer` workflow for a radar run because that workflow intentionally excludes local sources, while this radar must combine local Bug evidence with remote business knowledge.

Use a bounded retrieval sequence:

1. Resolve product, surface, module, feature, entry, role, version, and change profile before querying.
2. Run no more than five narrow `find` or `search` queries. Broad search results are candidates only; top-level abstracts do not prove that no deeper evidence exists.
3. Prefer indexed or known paths in this order: `accepted/`, current update packages, `normalized/testcase-atoms/`, then `sources/`. Use `list` or `glob` for directory routing and `grep` for exact terms when semantic search only returns summaries.
4. Call `read` for every remote URI used in the radar. Read at most eight selected evidence items unless the user explicitly asks for a broad knowledge audit. After candidate routing, pass the selected URI list to one batch `read` call when the provider supports it; do not issue one read call per URI merely for convenience.
5. Compare `product`, `surface`, `scope`, `valid_for/not_valid_for`, version, source date, and `applies_to/not_applicable_to`. An unknown applicability result cannot define a confirmed expected behavior.
6. Pass every read item through the remote evidence admission gate before using it in a risk:
   - **Independence:** mark it `independent_history`, `same_requirement`, or `unknown`. Material generated from the current requirement is `scope_audit_only`; it may reveal a missing PRD route but cannot support recurrence risk, prove a conclusion, or count as an improvement over a previous radar.
   - **Scope:** retain only the objects and conditions explicitly covered by the source. A member-only rule does not cover departments or roles; a path scenario does not automatically cover every cache, download, or install directory. Split the risk or keep the uncovered part conditional.
   - **Claim strength:** write one `claim_boundary` stating exactly what the item proves and does not prove. A testcase supports only its stated scenario and expected assertion. Do not add stronger algorithms, retry behavior, log detail, compatibility handling, or failure recovery unless another accepted source establishes them.
   - **Admission:** mark the item `selected`, `scope_audit_only`, or `rejected`. Only `selected` evidence may appear in a risk's `source_ids`; unknown provenance or applicability requires a conditional risk.
7. Deduplicate by Bug ID, atom/rule ID, source reference, and equivalent failure mode before ranking. Do not count the same Feishu Bug from local and remote stores twice.
8. Keep no more than five high-value remote additions in the user-facing radar. Zero or one remote addition is valid when that is all the evidence supports. Remote knowledge should add a missing risk dimension or correct a business boundary, not merely increase output length.
9. Within one requirement task, reuse remote search results and already-read evidence for the same normalized intent, resolved object, change profile, and source URI. Invalidate the reuse when the user changes a material scope, role, state, expected behavior, or evidence source. Do not persist this optimization across tasks.

Track remote retrieval as one of:

- `queried`: matching evidence was read and evaluated;
- `no_match`: the service worked but no applicable evidence remained after scope checks;
- `unavailable`: health, network, or authorization failed;
- `not_configured`: the MCP plugin or credential is absent;
- `skipped`: remote retrieval was intentionally unnecessary, with a reason.

For `unavailable` or `not_configured`, continue with the local Bug map and briefly disclose that remote knowledge was not checked. For `no_match`, say there is no matched remote rule/testcase evidence; do not describe the service as unavailable. Never call OpenViking write tools from a radar run.

Use two independent evidence orders:

- **Recurrence-risk order:** same-function online Bug, strong related Bug, tester experience, historical testcase, then AI inference.
- **Correct-behavior order:** current PRD/AC/current runtime evidence, current owner confirmation, applicability-matched `ACCEPTED_L1`, 2026 formal testcase, 2025 historical testcase, then normalized/candidate material.

A Bug can prove that a failure happened but may not define the current correct behavior. An accepted rule can define behavior within its scope but does not prove the current code implements it.

When the user provides a PRD, document, screenshot, or detailed requirement, start the answer with `需求识别` and state the real change model, such as `不是单纯样式调整，而是授权对象从成员扩展为成员/部门/角色`. If one to three direct or strong-related historical failures expose risks that the requirement does not state explicitly, follow with `历史雷达额外提醒` and summarize those concrete failures in one sentence. This should make the radar's added value visible immediately. Use `本次重点看` only when there is no sufficiently concrete historical reminder or when a short chain orientation is still needed; do not print both lines when they merely repeat the detailed risk headings.

Do not turn the orientation into marketing copy. Keep it factual and traceable to retained evidence. Do not assign `P0/P1` from evidence strength alone; use neutral wording such as `优先检查` unless product impact or an explicit severity basis is available. Remove generation-process words such as `新增直接历史` from user-facing evidence labels; write `直接历史`, `强相关历史`, or another stable evidence label. When a historical testcase materially contributes a risk, show a short recognizable testcase or source name when available instead of only saying `历史用例补充`.

Do not equate multiple affected entries with confirmed implementation reuse. Say `涉及`, `覆盖`, or list the affected entries when the requirement only names surfaces. Say `复用同一组件/接口/数据模型` unconditionally only when the PRD, diff, runtime evidence, or an accepted source confirms that relationship; otherwise write the related regression point conditionally. Before rendering, assign each failure mechanism to one primary visible item and remove repeated conditions or assertions from neighboring bullets. Internal dimensions may remain separate in the plan while their assertions render under one user-facing risk. A hierarchy-selection item should not also own disabled/deleted-object handling unless the same failure mechanism truly requires both.

When `radar-check --draft` reports `obligation_split_across_sections`, review whether one historical mechanism was split only to satisfy multiple internal dimensions. Merge those sections unless they contain materially different triggers and observable assertions that cannot be read clearly together. When it reports `risk_priority_saturation`, do not arbitrarily demote valid risks; either define the prioritization basis, order the risks without P0/P1 labels, or use reader-facing groups such as `首轮必测` and `扩展回归`. Warnings require judgment and do not replace the lossless-coverage gate.

If direct same-feature Bugs are sparse but the requirement is a model expansion or runtime-chain change, do not compress the answer to one or two items. Add strong related history and same-class inference with clear evidence labels.

## Model Expansion Changes

Some requirements are not just new UI; they expand the underlying object model. These must be actively expanded after the business object is resolved.

- **Authorization or permission model expansion:** applies when authorization, visible scope, effective members, roles, departments, data scope, or shared selector components expand from one object type to multiple object types, such as `成员` to `成员/部门/角色`. Check save paths that may clear authorization, list/detail/hover/display completeness, filter/statistics semantics, department hierarchy, role names/icons, data-permission overreach or underreach, disabled/deleted object fallback, operation logs, notifications, and every shared component entry.
- **List, filter, or field model expansion:** applies when a list adds fields, filters, display dimensions, exports, or new object types. Check list/detail consistency, filter/search/sort/pagination, exports, permission visibility, empty or historical data, refresh/relogin/reopen, and whether old filters still use the old single-object logic.
- **State or lifecycle expansion:** applies to purchase, renewal, enable/disable, delete/restore, recycle bin, expiry, effective/invalid states, or status migrations. Add lightweight checks for status after operation, refresh/relogin/reopen, logs/notifications, permission visibility, failure/cancel/retry/repeat operations, and historical data compatibility.

These expansion rules are not permission to blur concepts. For example, `账号中心` and `账号列表` still remain different account concepts; `云号管理` still does not imply `打开店铺` unless the requirement connects them.

When requirement analysis or tester experience adds material risks beyond the retained historical Bugs, make that judgment visible without duplicating the history section. For detailed model-expansion or shared-component changes, prefer a short section named `本次改动推导的易漏风险` over a generic `扩展回归面`. State once that these are requirement/test-experience inferences rather than direct historical Bugs. Each item should briefly connect `判断依据 -> 容易出现的失败 -> 本次检查重点`, usually in one or two sentences. Keep only three to five high-value inferences, and do not expose private chain-of-thought or expand them into full testcases.

## Chain-Level Client Changes

Some client changes are not isolated page features. For client low-level or runtime-chain changes such as `本地端口`, `端口分配`, `内核`, `资源包`, `缓存路径`, `升级`, `多开工作台`, `打开店铺`, `客户端本地服务`, or `客户端和内核通信`, do not narrow recall to only same-name Bugs. These changes can fail through adjacent chain nodes.

For these requests, actively check related scenarios in this order:

- Same-function direct Bugs, such as local-port access rules for a local-port change.
- Strong related chain Bugs, such as opening-store failures, startup queue blocking, URL launch, multi-workbench isolation, process residue, client-kernel communication, and port/resource release.
- Adjacent failure-handling risks, such as no prompt, no log, stale caller configuration, retry behavior, and recovery after restart.
- Ordinary QA supplemental checks, such as OS/firewall/VPN/security-software environment differences.

Start these answers with a one-sentence focus statement such as `本次重点看：端口占用、兜底分配、多开工作台、打开店铺、客户端-内核通信、内核本地端口访问`. Adapt the nouns to the current chain so the tester immediately sees the risk focus.

Keep the evidence boundary explicit. Business concept matching should stay strict, but chain-level client changes should have wider impact recall. Do not present adjacent chain Bugs as same-function direct history; label them as `强相关链路 Bug`, `相邻异常兜底推导`, or `建议补充检查`.

For local-port recalls, do not use `访问策略` as a generic synonym for local access control because Ziniao also has a separate access-policy capability. Prefer precise wording: `本地端口访问特例`, `全局白名单特例`, and `本地端口访问限制`.

## Recall Workflow

1. Identify the test target from the user's wording: client, admin, store, mobile, kernel, account, device, cloud number, security, service, AI, plugin, or another Ziniao module.
2. If the target contains `账号`, classify it as 紫鸟账号 / 登录账号 or 店铺账号 / 平台账号 using the Product Model account terminology before running recall. Build search queries with the resolved terms, and avoid evidence from the other account type unless explicitly marked as adjacent and justified.
3. Identify the change type as `旧功能改动`, `新功能新增`, or `未说明`. Use the `Change Type` rules above to choose the output wording.
4. Identify whether the request is a model expansion, list/filter/field expansion, state/lifecycle change, or chain-level client change. Apply the relevant expansion rules before finalizing the response.
5. Refresh the governed OpenViking Bug cache before the first radar recall in a task. Fetch the small manifest first; when its source SHA-256 matches the local validated cache, return immediately without downloading the full normalized dataset or rebuilding indexes. Remote failure must not erase or partially rebuild the cache; continue with the last validated local mirror and disclose `local_fallback` briefly:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/refresh_openviking_bug_cache.ps1
   ```

6. For one primary query, the legacy local recall command remains available:

   ```powershell
   py scripts/landmine.py recall "<module or feature>"
   ```

7. When requirement analysis produces multiple narrow queries, prefer one `radar-search` call. It performs the grouped primary recall and all scenario/Bug-detail queries in one process while sharing read-only OpenViking mirror data, alias configuration, and scenario indexes:

   ```powershell
   py scripts/landmine.py radar-search "<primary feature>" --related "<related query 1>" --related "<related query 2>" --explain
   ```

   Normalize and deduplicate equivalent queries before execution. This fast path must use the same scoring, ranking, recency, scenario, and evidence rendering functions as the legacy commands. If it fails, fall back to the legacy commands without changing thresholds.

   Treat the grouped result as the task's immutable local candidate pool. Reuse it
   for the structured plan, rendered radar, handoff, and later coverage mapping;
   do not rerun recall, scenario-search, or bug-search for those separate outputs.
   A compact Chinese requirement phrase must retain its embedded specific feature
   terms during scoring. For example, `店铺账号锁定申请审批` must still score
   `账号锁定` evidence; broad `账号管理` or `审批` aliases cannot replace a matching
   same-feature Bug merely because they rank earlier.

8. For a single narrow feature, menu, or requirement-specific question, the scenario index command remains available:

   ```powershell
   py scripts/landmine.py scenario-search "<module or feature>" --explain
   ```

9. If recall has no strong match or the user asks for concrete historical Bugs, the legacy detail command remains available. `bug-search` prints matching scenario-index hits first when available, then lists individual Bug evidence:

   ```powershell
   py scripts/landmine.py bug-search "<module or feature>" --explain
   ```

10. Build a local candidate pool from the grouped recall, scenario index, and detail search. Do not loosen search thresholds merely to make the answer longer, but do not discard same-model or shared-component evidence before the risk-dimension audit.
11. When the OpenViking MCP is available, run the bounded remote retrieval described above. Submit independent accepted-rule and historical-testcase searches concurrently or in one batch when the provider supports it, then batch-read only admitted candidates. Query accepted business rules and historical testcase atoms for the resolved object; do not repeat the synchronized online-Bug search. Record the historical testcase result in `historical_testcase_review` even when no testcase is selected. A search that returns candidates is `queried`, not `no_match`; each candidate must be marked `selected`, `scope_audit_only`, or `rejected` with a concrete reason.
    Use one search/metadata round per evidence family. Shortlist by resolved object,
    surface, failure mechanism, and source status before reading bodies; never
    serially open every hit. Run a second targeted query only when the first round
    exposes a concrete unresolved term or conflicting accepted evidence, and
    record that reason in the plan. This bounds latency without dropping an
    evidence family or weakening its admission checks.
12. Apply the independence, scope, and claim-strength admission gate to every remote candidate. Merge and deduplicate only admitted `selected` evidence with the local pool; keep `scope_audit_only` material outside risk evidence. Rank recurrence risk and correct-behavior authority separately, then retain only remote items that correct a boundary or add a missing high-value dimension. For every selected historical testcase candidate, record the plan evidence ID and the risk IDs whose reasoning it changed. The radar handoff remains a synthesized set of risks and obligations; it does not copy historical testcase rows into the generator.
13. For model-expansion requests, search related model nodes even when exact same-name Bugs are sparse, such as department hierarchy, role display, data scope, disabled/deleted objects, logs, notifications, and shared component entries.
14. For chain-level client changes, run or mentally include adjacent scenario searches such as `打开店铺`, `多开工作台`, `客户端和内核通信`, `进程残留`, `启动卡住`, or `资源/端口释放` when those nodes plausibly depend on the changed capability.
15. If no strong match exists, say so and fall back to nearby risks from the same category or module. Do not invent historical Bugs. Distinguish local no-match, optional remote knowledge `no_match`, and cache preflight `local_fallback`.
16. Before finalizing a standalone detailed PRD, model-expansion, chain-level, or disputed radar response, read `references/radar_quality_gate.md` and perform its semantic coverage review, including the mandatory final claim-boundary audit after the draft is written. Skip this detailed rendering gate for an integration request explicitly carrying `radar_profile=concise`; the orchestrator's handoff validator is the applicable gate. Run the full draft validator once after the final candidate set and wording stabilize; do not repeatedly validate unchanged intermediate drafts. This is a quality check, not a requirement to use fixed wording or fixed item counts.
17. For high-impact, disputed, or regression-comparison work, validate the internal structured plan and rendered draft when practical:

   ```powershell
   py scripts/landmine.py radar-check <plan.json> --draft <radar.md>
   ```

   Use `--benchmark` only for evaluation. Normal production recall must not read benchmark expectations.
18. When the user provides a new pitfall, normalize it into the schema in `references/schema.md` before appending it to `data/landmines.jsonl`.
19. After changing aliases, ranking rules, scenario seeds, seed landmines, or radar quality rules, run:

   ```powershell
   py scripts/landmine.py eval
   py scripts/landmine.py radar-eval
   ```

## Detail Import Workflow

Use this when the user asks to refresh Feishu online defects with remarks, reproduction steps, actual results, expected results, or fix plans.

Online Bugs are not static. Refresh this dataset on the configured automation cadence, or immediately when the user says recent online Bugs should be included. The Codex automation is named `每周同步紫鸟线上缺陷雷区地图`; preserve its configured schedule unless the user asks to change it. Refresh the rolling 182-day view and the broader historical view back to back in the same run so their snapshots cannot drift.

The Feishu view may be configured as a rolling recent window, such as latest 182 days. Treat that view as "current-window freshness", not as the whole history. During detail import, Bugs present in the current view receive `current_182d`; Bugs in the broader view receive `historical_view`; Bugs already in `all_bug_details.jsonl` but absent from both remain in the long-term archive. `window_status` is derived for compatibility.

Keep direct query evidence above alias-expanded evidence. Historical archived Bugs remain eligible when they directly match the feature or failure pattern, but broad sibling aliases must only widen recall and must not outrank a direct current or archived match.

1. Refresh the rolling 182-day view, then immediately refresh the broader historical view:

   ```powershell
   py scripts/landmine.py import-feishu
   py scripts/landmine.py import-feishu --view-id ZZdtquUvR --view-url "https://project.feishu.cn/3zobdi/workObjectView/zxqx/ZZdtquUvR"
   ```

2. Refresh every Bug currently inside the rolling 182-day view without `--resume`, so changed remarks, reproduction steps, and fix plans are not hidden by the cache:

   ```powershell
   py scripts/landmine.py import-details --source data/feishu_raw/view_Khmxw2UDR_normalized.json --current-source data/feishu_raw/view_Khmxw2UDR_normalized.json --flush-each
   ```

   This updates both the current-window cache and `all_bug_details.jsonl`. Do not replace the long-term archive with only the latest view export.

3. Backfill only missing historical details with `--resume`, while keeping the rolling view as the membership authority:

   ```powershell
   py scripts/landmine.py import-details --source data/feishu_raw/view_ZZdtquUvR_normalized.json --current-source data/feishu_raw/view_Khmxw2UDR_normalized.json --resume --flush-each
   ```

4. Re-clean local text if sanitization rules changed:

   ```powershell
   py scripts/landmine.py sanitize-details
   ```

5. Recompute both view memberships, then build searchable normalized evidence:

   ```powershell
   py scripts/landmine.py refresh-view-memberships
   py scripts/landmine.py normalize-bugs
   ```

   By default this reads `all_bug_details.jsonl` when it exists, so older Bugs remain searchable even after they leave the rolling Feishu view.

6. Refresh generated clusters and search landmines from the normalized archive's `current_182d` membership:

   ```powershell
   py scripts/landmine.py build-scenarios
   py scripts/landmine.py cluster-feishu --source data/normalized_bugs.jsonl
   py scripts/landmine.py sync-clusters
   ```

7. Validate recall quality before publishing:

   ```powershell
   py scripts/landmine.py eval
   py scripts/landmine.py radar-eval
   ```

8. Publish the validated archive to OpenViking and verify exact bytes, IDs, fields, three-layer counts, and semantic summaries:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/sync_openviking_bugs.ps1
   powershell -ExecutionPolicy Bypass -File scripts/verify_openviking_bugs.ps1
   ```

If publication or verification fails, keep the existing remote dataset and report the failure; do not claim the scheduled synchronization succeeded. Radar recalls on other machines continue from their last validated local cache until a later preflight succeeds.

The detail import strips image URLs and HTML from remarks, keeps only text evidence, and must not persist people fields such as role members, emails, tokens, cookies, or accounts.

## Evidence Discipline

Always separate the recall result into evidence levels:

- **Same-feature or strongly related historical Bug:** the target feature or a close synonym appears in Feishu evidence or a tester note. Lead with these and cite the short Bug titles or IDs. Use this label instead of claiming every hit is an exact same-name Bug.
- **Cluster-derived risk:** the target belongs to a broader repeated pattern, such as list filtering, permissions, cache consistency, resource upgrades, or kernel behavior. Mark these as broader risk, not feature-specific history.
- **Suggested supplemental check:** a reasonable QA design point without direct local evidence. Put these last and label them as suggestions.

For narrow feature requests such as bookmarks, coupons, popups, search, or authorization, first search exact and synonym terms in the local data before giving generic checks. If exact matches exist, do not let generic clusters dominate the answer.

When explaining why a recommendation was made, state whether it came from direct Feishu Bugs, a generated cluster, or testing design inference.

For the exact output format, read `references/recall_output.md` when modifying this skill or when the response shape is disputed. For detailed requirements, model expansions, chain-level changes, comparisons with a previous answer, or any quality dispute, also read `references/radar_quality_gate.md`.

## Output Shape

Keep a radar compact but not under-covered. Optimize for experienced testers who need to identify recurrence and omission risks before writing or executing cases. Keep details risk-shaped: evidence, why it applies now, trigger, likely failure, easy-to-miss symptom, and minimum test data. Do not turn the radar into formal testcases unless the user asks.

Use `references/recall_output.md` as the single source of truth for section order, evidence labels, density, and examples. Use `references/radar_quality_gate.md` to verify semantic coverage and guard against regressions where stricter business boundaries accidentally make the answer less useful.

Concrete requirements in `data/radar_benchmarks.json` are evaluation fixtures only. They must never become production routing rules or mandatory output content for unrelated requirements. When a fixture exposes a failure, generalize the underlying change profile, evidence rule, or coverage invariant before changing production instructions.

## Boundaries

- Do not paste secrets or MCP tokens into files.
- Do not treat Feishu status counts as current unless queried in the current turn.
- Do not use global defects when the target view or target filter is unavailable.
- Do not write back to Feishu unless the user previews and confirms the exact write.
- Do not put the full defect database into this `SKILL.md`; keep growing data in `data/landmines.jsonl`.

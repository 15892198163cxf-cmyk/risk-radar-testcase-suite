# Recall Output Guide

When answering a pre-test recall, structure the response by evidence strength and practical risk. The purpose is to remind testers which historical online Bugs may recur and which requirement-specific areas are easiest to miss, not to produce a beginner tutorial or a full testcase set.

The radar must still output test points. Convert each retained high- or medium-priority risk into at least one concise, executable focus: what condition, identity, state, entry, data shape, or operation to exercise, and what result or failure symptom to observe. Keep it at test-point granularity; do not expand into testcase IDs, exhaustive preconditions, numbered procedures, or full expected-result blocks unless the user explicitly asks for testcases.

Before selecting final items, use this synthesis order: resolve the object, recall a broad candidate pool, correct true business mismatches, build an applicability bridge, audit requirement-specific risk dimensions, group historical evidence into failure-mechanism obligations, label evidence strength and business priority independently, and compress duplication last. Product knowledge may demote incorrectly scoped evidence; it must not silently remove a useful same-model, shared-component, or failure-mode risk.

Within one task, standalone-style rendering and workflow handoff share one
canonical radar result. They must retain the same risk identities, priorities,
evidence types/source IDs, executable test points, boundaries, and material
questions; a concise view may shorten prose or merge headings only. Independent
model runs are not expected to produce identical risk IDs, grouping, order, or
wording. Compare independent runs by retained failure mechanisms, source-backed
history, material test points, boundaries, and explicit exclusions.

For detailed, disputed, or regression-compared requirements, use `risk_model.md` and create the internal plan from `radar_plan_schema.md` before drafting. The plan must inventory named impacts, assess every generic dimension as applicable or not applicable, map evidence and failure-mechanism obligations to risks, and record exclusions. Render every high- and medium-priority planned risk and obligation once, then compress only duplicate wording. One risk may render several equivalent Bugs when their mechanism, trigger, and assertion are preserved. Do not show the internal JSON unless requested.

For each direct or strong related item, the reader should be able to tell: what historically failed, what current object or shared dependency connects it, which present change can trigger it, and what observable result to check. If the dependency or trigger is unknown, write the point under a concrete condition such as `若本次实现复用了该本地服务...`; do not leave an unconditional chain claim in the main history section.

Preserve explicit negative and exception rules such as permanent retention, no automatic cleanup, no historical migration, no restoration of old bindings, excluded object types, and operations that intentionally do not exist. These often describe the exact omissions most likely to escape ordinary testcase generation.

If the PRD contradicts itself, do not write either interpretation as an unconditional test expectation. Use `若以...为最终口径` or equivalent wording, keep the conflict under `需求疑点`, and separate the stable checks that remain valid under both interpretations.

## Required Order

Start with the change type when it is known or can be safely inferred:

- `旧功能改动`: say it is a regression-risk recall and lead with history that may recur.
- `新功能新增`: say same-name history may not exist and separate same-module evidence from design inference.

For PRD, document, screenshot, or detailed requirement analysis, add concise orientation before the evidence sections when it improves practical use:

- `需求识别`: state the real change model and object boundary, such as `这是店铺/平台账号授权旧能力增强，不是紫鸟账号中心；核心不是样式，而是授权对象从成员扩展为成员/部门/角色`.
- `历史雷达额外提醒`: when retained direct or strong-related evidence exposes requirement-unstated risks, summarize one to three concrete historical failures in one sentence, such as `历史上曾发生只改账号名称却误清授权、选择部门没有完整选中、无授权权限仍出现授权入口`. This is the preferred orientation because it immediately shows what historical recall adds beyond ordinary requirement analysis.
- `本次重点看`: use a compact risk-focus sentence only when there is no sufficiently concrete historical reminder or when a runtime-chain request still needs orientation. Do not show both lines when they say substantially the same thing.

Keep orientation factual, evidence-backed, and short. Do not assign `P0/P1` solely from evidence strength; use `优先检查` unless product impact or explicit severity supports a formal priority. User-facing evidence labels must not contain generation-process wording such as `新增直接历史`; use stable labels such as `直接历史` or `强相关历史`. For a selected historical testcase, include a short recognizable testcase or source name when available so the evidence remains traceable.

Do not write confirmed reuse merely because several entries are affected. Use `涉及` or `覆盖` for named surfaces; reserve unconditional `复用同一组件/接口/数据模型` for a confirmed implementation relationship. Otherwise use a visible condition such as `若三个入口复用同一选择组件`. Before finalizing, give each failure mode one primary section and remove repeated conditions or assertions from adjacent bullets. User-facing evidence boundaries should describe source categories such as `历史缺陷`, `已验收业务规则`, or `历史用例`; avoid generation-timeline wording and successful-retrieval implementation names.

1. `同功能/强相关历史 Bug`
   - Use only direct or close feature-specific Bugs or tester notes.
   - Include short Bug IDs or titles.
   - These checks are the highest priority.
   - Same keyword is not enough. The business object, entry, field/interface, or execution-chain failure point must match closely.

2. `同类雷区推导`
   - Use generated clusters or broader repeated patterns.
   - State why the pattern applies to the requested feature.
   - Do not present these as direct feature history.

Remote OpenViking evidence may be inserted where it changes the tester's decision, but it must keep its own label:

- `已验收业务规则`: an applicability-matched `ACCEPTED_L1` rule that clarifies correct behavior or scope. It is not proof of current implementation.
- `历史用例补充`: a current formal testcase or lower-weight historical testcase that adds an easy-to-miss role, state, entry, data shape, or version combination. It is not an online Bug.
- `待确认知识`: a candidate, temporary testcase, unknown-scope atom, or conflicting rule. Keep the related risk conditional or omit it from the main radar.

When a version 4 or 5 risk has assertions with different bases, keep one readable risk heading but label the subclaims minimally, for example `历史复发`, `需求约束`, `业务规则`, or `测试推导`. Do not label the whole point as direct history when only one subclaim is Bug-backed. This is provenance clarity, not a request to expose assertion IDs or print more sections.

For a conditional assertion, keep a short visible condition such as `仅当复用同一组件时`, `确认当前平台范围后`, or `若本次 diff 涉及该链路`. Do not render only the risk phrase while dropping the condition that limits its applicability.

Do not add a separate remote section merely to prove that OpenViking was queried. Merge a matched rule into the relevant risk when concise, or use a short `业务规则/历史用例补充` section when multiple items materially add coverage. Keep no more than five visible remote additions by default; zero or one is valid when that is all the evidence supports.

3. `本次最该盯的风险`
   - Synthesize the highest-priority recurrence and omission risks for this requirement.
   - Keep this section short; it should guide what to look at first, not duplicate every section.

4. `本次改动推导的易漏风险` or `扩展回归面`
   - For detailed model expansion, shared-component change, or PRD analysis, prefer `本次改动推导的易漏风险` when requirement analysis or tester experience materially adds coverage beyond the historical Bugs.
   - State once that these items are requirement/test-experience inferences rather than direct historical Bugs.
   - Make the rationale inspectable: briefly connect `判断依据 -> 容易出现的失败 -> 本次检查重点`. Do not expose private chain-of-thought.
   - For short feature recalls, `扩展回归面` remains acceptable for lower-priority adjacent coverage such as lists, filters, permissions, state refresh, logs, and runtime effects.
   - Do not repeat the highest-priority risks already listed above unless a brief reminder is needed. Keep three to five high-value points rather than growing into a full testcase set.

5. `建议补充检查`
   - Use ordinary QA design reasoning.
   - Keep it short.
   - Mark it as supplemental.

## Default Density

Do not make recall longer by lowering matching thresholds or mixing in weak Bug hits. Instead, keep evidence strict and add clearly labeled adjacent checks. Detailed output is acceptable when it improves readability and practical judgment, but keep the detail risk-shaped: evidence, why it applies now, trigger conditions, likely failure modes, easy-to-miss symptoms, and key data. Avoid formal testcase formatting unless explicitly requested: no testcase IDs, no coverage matrix, and no full precondition/step/expected-result blocks.

When OpenViking is configured, semantic search abstracts are candidate routing only. Use accepted rules first, then current formal testcase atoms, and call `read` on every selected `viking://` source. Distinguish `no_match` from `unavailable`; disclose service failure briefly, but do not clutter a successful radar with MCP implementation details.

Concrete benchmark examples in this guide or `data/radar_benchmarks.json` are regression fixtures, not universal answer templates. Generalize the change profile or evidence rule; never copy a fixture's entry list into an unrelated requirement.

For account-related recalls, state the resolved account type when it materially affects evidence:

- `紫鸟账号 / 登录账号`: account center, account settings, member-login account, phone binding, security center, login identity.
- `店铺账号 / 平台账号`: account list, account management, platform/store account, authorization members, escrowed login credentials, primary/additional account.

Do not use direct-history wording when the evidence belongs to the other account type. If such evidence is still useful, put it under `同类雷区推导` and say it is adjacent only.

For evidence strength, treat same business object + same entry/field/interface as direct evidence when the current delta can reach the same mechanism. Treat a demonstrated shared component, data model, lifecycle, or runtime dependency as strong related evidence even across entries or modules. Treat the same interaction pattern without a shared mechanism as adjacent. Treat keyword-only matches across different business objects as non-applicable and usually omit them unless they explain an explicit ambiguity.

Do not use evidence strength as a synonym for priority. A direct historical issue can be medium priority for the current change, while an explicit high-impact security or data-loss requirement can be high priority without direct history. Show both honestly when the distinction matters.

Boundary tightening is not risk narrowing. After resolving the correct business object, expand by requirement type and label evidence strength. Do not make the radar less useful just because some evidence is adjacent rather than direct.

For authorization or permission model expansion, such as `授权成员` expanding to `成员/部门/角色`, actively cover:

- save paths that might clear or overwrite authorization;
- display completeness in lists, dialogs, details, hover, logs, and notifications;
- filter and statistics semantics after the object model changes;
- department hierarchy, child departments, and no-permission departments;
- role name/icon/hover display and role data scope;
- over-permission and under-permission in visible members/departments/roles;
- disabled/deleted object fallback and selected-object re-display;
- shared component entries that reuse the selector, such as account authorization, cloud-number authorization, and access-policy effective members.

These points can use same-model or adjacent Bugs, but they must be labeled as `强相关历史 Bug`, `同类雷区推导`, or `相邻证据`; do not call them exact same-feature Bugs unless the evidence really matches.

For list, filter, or field model expansion, actively cover list/detail consistency, filter/search/sort/pagination, export, permission visibility, empty or historical data, refresh/relogin/reopen, and old logic that still assumes the previous single object or field.

For state or lifecycle changes, use a lighter expansion: status after operation, refresh/relogin/reopen, logs/notifications, permission visibility, failure/cancel/retry/repeat operations, and historical data compatibility.

For client low-level or runtime-chain changes, use a wider but still labeled evidence model. Examples include `本地端口`, `端口分配`, `内核`, `资源包`, `缓存路径`, `升级`, `多开工作台`, `打开店铺`, `客户端本地服务`, and `客户端和内核通信`.

Start with a short focus sentence before the evidence sections. Example: `本次重点看：端口占用、兜底分配、多开工作台、打开店铺、客户端-内核通信、内核本地端口访问。` This is not a testcase title; it is a quick radar orientation for the tester.

- `同功能直接 Bug`: the same capability or same execution point broke before.
- `强相关链路 Bug`: adjacent chain nodes where the changed capability can plausibly surface, such as opening-store failures, startup queue blocking, URL launch, multi-workbench isolation, process residue, client-kernel communication, or port/resource release.
- `相邻异常兜底推导`: nearby failure-handling evidence, such as no response, unclear prompt, missing log, stale caller config, retry/recovery failure, or environment-specific blocking.
- `建议补充检查`: ordinary QA checks without local Bug evidence, such as firewall, VPN, security software, or OS-level port restrictions.

This wider model is for client runtime-chain changes only. It must not be used to loosen business-object boundaries such as `账号中心` versus `账号列表`, or `云号` versus `打开店铺`.

For local-port recalls, avoid saying generic `访问策略` unless the product requirement explicitly means Ziniao access policy. Prefer `本地端口访问特例`, `全局白名单特例`, and `本地端口访问限制`. If the commit diff or PRD does not identify the exact service or caller chain, add a short evidence boundary: `未拿到具体调用链时，不能确认 IP 检测、插件通信、内核通信是否必然受影响；如果它们依赖该端口，则纳入高优先级回归。`

For `旧功能改动`, the default answer should be layered:

- `历史复发重点`: 3-5 direct or close Bug-backed checks when available.
- `扩展回归面`: 3-5 same-module, same-data, same-permission, same-list/filter, same-state-refresh, or same-login/launch-flow checks. These are adjacent risks, not direct Bug history.
- `测试数据准备`: the minimum accounts, roles, departments, permissions, statuses, and boundary values needed for execution.

For `新功能新增` or `旧能力增强`, keep the same evidence boundary even when there are no same-name Bugs:

- `同功能/强相关历史 Bug`: exact or close Bug evidence only; say "未查到同名历史线上 Bug" when applicable.
- `同类雷区推导` or `扩展回归面`: adjacent same-module, same-data, same-permission, list/filter, state-refresh, login/launch, log, or security-sensitive risks.
- `本次最该盯的风险`: only the highest-priority recurrence or omission risks.
- `建议补充检查`: ordinary QA design checks that are not backed by local Bug evidence.
- `测试数据准备`: minimum executable data and roles.
- `需求疑点`: contradictions or unclear expected results from the requirement.

If the direct Bug evidence is strong and numerous, shorten `扩展回归面`. If direct evidence is sparse, add more adjacent checks, but explicitly say they are inferred from the module or interaction pattern.

For client chain-level changes, sparse direct evidence is not a reason to shrink the radar to one item. Include the strongest related chain Bugs and adjacent fallback risks, then state the evidence boundary clearly.

Before saying ports, paths, processes, caches, or settings must be independent per workbench/store, determine whether the resource is global, client-owned, workbench-owned, or store-owned. When unknown, check correct mapping and no cross-impact without prescribing uniqueness or release timing. For example, a shared client service may legitimately use one port, while independent store services may require separate ports.

For authorization, permission, list/filter/field, or state/lifecycle model changes, sparse direct evidence is also not a reason to shrink the radar to one item. Use the relevant expansion risks above and keep evidence labels explicit.

When describing impact, use narrow wording such as `被删除的 Passkey`, `对应账号`, `当前配置`, or `这条云验证码密钥`. Do not imply global feature failure unless the requirement or evidence says the whole feature is affected.

## Bad Pattern

Do not mix direct Bugs and generic checks into one flat list. It makes inferred advice look like confirmed history.

Do not present an OpenViking accepted rule as a historical Bug, a testcase atom as proof of an escaped defect, or any remote item as proof that current code implements the rule. Do not duplicate the same Feishu Bug from the local archive and OpenViking.

Do not omit `扩展回归面` merely because the request is a new requirement. New requirements often lack same-name history, so the adjacent regression surface is where the landmine map is most useful.

Do not turn Ziniao surfaces into generic multi-terminal checks. 管理系统 is an online page inside the Ziniao client; 店铺内 is an isolated browser-kernel environment. For 管理系统 purchase/order flows, default to 管理系统 visibility and consistency unless the requirement explicitly affects 客户端 shell or 店铺内 runtime.

Do not let the shared word `账号` override domain meaning. `账号中心/账号设置` is 紫鸟登录账号 by default; `账号列表/账号管理/授权成员` is 店铺账号 by default. A true historical Bug from the wrong account type is still wrong evidence for the current requirement.

Do not turn 云号 requirements into 打开店铺 requirements unless the requirement explicitly connects them. Do not put IP 检测 under 管理系统 by default; it belongs to the store-opening/device-network environment chain, with automatic launch-time environment safety detection and explicit store/device detection-page checks. Do not merge 监管 and 访问策略 evidence unless the requirement crosses both capability families.

Do not overstate old Bugs. Permission, data, interface, authorization, cookie isolation, and state-consistency Bugs can keep normal reference weight when core logic is unchanged. UI-layout, old-kernel-specific, V5-only, or rebuilt-module Bugs should be downgraded unless the current requirement touches the same chain.

Do not make client chain-level recalls too narrow. If a local-port, kernel, resource, cache, upgrade, multi-workbench, or opening-store change can affect runtime behavior, include the relevant launch, communication, process, release, and recovery risks. Mark adjacent Bugs as chain-related, not direct same-function history.

Do not write `访问策略不能被兜底绕过` for local-port evidence unless the current requirement really touches Ziniao access policy. Use local-port-specific terms instead: `本地端口访问特例`, `全局白名单特例`, `本地端口访问限制`.

Do not make model-expansion recalls too narrow. If a requirement expands an authorization object, permission scope, list field, filter dimension, or state model, include the likely affected display, save, filter, permission, log, notification, and compatibility surfaces. Mark adjacent Bugs as model-related, not direct same-feature history.

## Good Pattern

For "我要测书签相关的":

- Direct Bugs: file rename/link edit Enter creates a new item; deleted bookmark filter issue; default bookmark jump wrong; Firefox kernel bookmark loading.
- Cluster Risks: list filtering and cache consistency.
- Supplemental: invalid URL, duplicate name, multi-window edits.

For "账号列表旧功能改动，新增店铺字段可修改":

- Assumption: 旧功能改动, so this is regression-risk recall.
- Direct Bugs: account list filtering, authorization-member consistency, edit-account field persistence, operation log/permission side effects.
- Cluster Risks: list refresh, detail/list consistency, permission visibility, batch state.
- Supplemental: only add checks specific to the changed field and entry.

For "创建成员旧功能改动":

- Assumption: 旧功能改动, so this is regression-risk recall.
- Direct Bugs: username whitespace compatibility, copied enterprise-login password escaping, member-management action failures, department/member data scope.
- Adjacent Regression: role assignment, department selection, list refresh/search, permission visibility, invitation/login result.
- Test Data: boss/admin/member roles, first-level and child departments, duplicate and deleted members, special usernames/passwords.

For "账号列表新增一个新功能":

- Assumption: 新功能新增, so same-name history may not exist.
- Direct Bugs: only include exact or close feature evidence if present.
- Same-module Risks: account list permissions, filtering, refresh, labels, batch operation, detail consistency.
- Supplemental: infer from the new feature's interaction type, data type, permission model, and affected pages.

For "账号支持按成员或部门或角色授权":

- Requirement Recognition: 店铺/平台账号授权旧能力增强; core change is authorization object model expanding from member-only to member/department/role, not just dialog style.
- Focus: 授权保存不误清、对象展示完整、授权筛选语义、部门子级、角色名/图标/hover、数据权限、禁用成员标记、日志/通知、账号/云号/访问策略共享组件一致性.
- Direct Bugs: edit-account save clearing authorization; account-list authorization filter incorrect; multiple members/roles displayed incompletely; authorization-dialog search repeatedly requesting data and causing CPU/page lag.
- Related Model Bugs: department child-member omissions, member visibility overreach, role names displayed as ID or blank, disabled-member visibility inconsistency.
- Evidence Boundary: cloud-number authorization and access-policy effective members are shared-component regression surfaces unless the evidence is directly from account authorization.
- Scope Boundary: Android return failure belongs in extension regression unless the current requirement changes mobile/client-shell routing; operations-admin role-name blank is weak adjacent evidence, not direct account-authorization history.

For "优化本地端口分配兜底":

- Assumption: 客户端底层旧功能改动, so this is chain-level regression-risk recall.
- Focus: 端口占用、兜底分配、多开工作台、打开店铺、客户端-内核通信、内核本地端口访问.
- Direct Bugs: local-port access rule, 本地端口访问特例, 全局白名单特例, and 本地端口访问限制.
- Strong Chain Bugs: multi-workbench URL launch process residue, opening-store startup queue blocking, client-kernel communication still using stale ports.
- Adjacent Fallback: occupied port range, all ports unavailable, no prompt/log, restart recovery, firewall/VPN/security-software blocking.
- Test Data: occupied default port, multiple occupied candidate ports, multi-workbench enabled, Chrome and Firefox kernel stores, batch opening stores.
- Evidence Boundary: without commit diff or PRD caller-chain detail, IP detection, plugin communication, and kernel communication should be phrased as conditional high-priority regressions only if they depend on the changed port service.

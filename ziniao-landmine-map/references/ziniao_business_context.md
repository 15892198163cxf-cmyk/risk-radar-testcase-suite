# Ziniao Business Context

Use this reference as a routing aid for the landmine radar. It distills two knowledge-base answers supplied by the user:

- `紫鸟业务知识底稿 — Bug 驱动测前风险雷达参考.md`: primary source for concept boundaries, PRD routing, evidence-strength rules, and examples.
- `111.txt`: supplemental short source for module map and compact wording.

These source materials are useful, but not authoritative on their own. If they conflict with user-confirmed rules, live PRD text, or Feishu Bug evidence, the user-confirmed/current evidence wins. Do not copy long product-description text into answers; convert it into risk routing and evidence boundaries.

## Confirmed Overrides

These rules have been confirmed in conversation and should override both source files:

- `账号中心`, `账号设置`, `紫鸟账号`, `登录账号`, and `成员账号` belong to the Ziniao login/member-account concept.
- `账号列表`, `店铺账号`, `附加账号`, and `主账号` belong to store/platform-account management.
- `附加账号` has independent login credentials, but reuses the main account's bound device environment, including network/IP/proxy and browser fingerprint/security environment.
- `设备` is the configuration/resource unit that provides a store account's network environment and security environment. A bound device determines network exit/proxy IP and browser fingerprint/security environment.
- `IP检测` is part of the opening-account/browser environment safety detection chain and is also visible through explicit store/device detection pages. It is not only a user-opened detection page.
- Opening-store risk should start from business invariants: account permission, a resolvable store environment, a usable kernel, a usable device/network route, and target-site reachability. Add proxy only for device types that use one; add existing session/cookie loading and escrowed credential autofill only when configured or relevant; add plugins, access policy, and supervision only when enabled; add local service, local ports, process reuse, and cache internals only when the change, diff, or historical evidence connects them to the failure.
- `本地端口` mainly supports opening stores and client-to-kernel communication.
- 云号 requirements do not imply opening-store checks unless the PRD explicitly connects cloud numbers to store launch/runtime.
- 云号 has two separate relationships: `授权成员` for managing/viewing SMS or call records, and `绑定账号` for recording which store/platform account uses the number.
- `事中监管`, `添加监管账号`, and `告警方案` are the supervision/监管 family. `访问策略` and `会员安全策略` are the access-policy family. Store-operation supervision is not the same execution path as management-system login, operation, or permission logging, even when those logs are presented under the same broad security area.
- Common roles are BOSS, 超级管理员, 管理员, and 普通成员. Except for BOSS, roles can have customized permissions.
- If a feature does not depend on opening stores, client local behavior, or store runtime, default to management-system checks.
- 书签 is a store-inside feature; test the 店铺内 effect by default.
- 多开工作台 mainly affects opening stores; accounts opened in different workbenches must not affect each other.
- Any visible page copy needs English translation.
- Feishu `所属模块` can be imprecise. Use title, steps, actual result, expected result, and fix plan to decide true business ownership.

## Module Map

Use this map to route PRD scope before recalling Bugs.

- **客户端:** app shell, local service, local ports, kernel, resource packages, upgrades, multi-workbench, client settings, native integrations. Default risks: startup, update/upgrade, port conflict, client-kernel communication, process residue, local cache/resources, multi-workbench isolation.
- **管理系统:** online page opened inside the Ziniao client. Default risks: CRUD/list/detail consistency, form validation, permissions, filters/search/pagination/sort, operation logs, status refresh, visible copy translation.
- **店铺内:** isolated browser-kernel environment for each store/account. Default risks: page rendering, navigation, cookie/cache isolation, environment safety detection/IP network checks, proxy, explicit detection pages, plugins, bookmarks, downloads, access-policy execution, supervision capture, multi-workbench isolation.
- **运维后台:** internal operations/config/data tools. Default risks: configuration scope, query/list correctness, data consistency, audit/logging, internal actions not leaking unexpected user-facing effects.
- **官网 / 安全中心:** public/safety/login/download/help pages. Default risks: visible copy, download/help-link validity, login/security flow, translation, page loading.
- **插件:** management entry may be in management/client surfaces, but runtime effect is usually store-inside. Default risks: install/uninstall/update, runtime compatibility with kernel/platform page, isolation between stores, permission scope, page impact.

## Management-System Submodules

- **首页:** dashboards, account dynamics, account balance, notices, shortcuts. Watch data accuracy, permission-filtered data, empty states, refresh/loading.
- **账号管理:** store/platform account management: add/edit/delete/authorize store accounts, bind devices, open accounts, main/additional accounts, labels, escrowed credentials, list/detail consistency.
- **设备管理:** device purchase/import/management/binding/renewal. Watch device state, binding/unbinding, proxy/IP/fingerprint-related configuration, imports, recycle/trash behavior, renewal state.
- **云号管理:** purchase, list, authorization, account binding, replacement, SMS/code/call-record display. Watch payment/order/state consistency, assignment/reclaim, member authorization, account binding, replacement records, old/new number behavior. Do not default to opening-store checks.
- **安全监管:** access policy, supervision, webpage resource management, screen watermark, logs. Keep access-policy and supervision evidence separate unless the PRD crosses both.
- **费用管理:** recharge, balance, order, paid service, invoice, rights/fee summary. Watch rights/status/order consistency, expiry/renewal transitions, payment failure/cancel/retry. Device/cloud-number renewal entries may live in their own modules, but fee/order consistency belongs here.
- **企业管理:** member management, department management, role/permission management, certification, enterprise settings, app management. Watch member/department/role relationships, custom permissions, data scope, invitation/login state.
- **紫鸟账号中心:** enterprise info, login method, account security, notification management, phone/binding/security-center flows. Do not mix with store-account `账号管理`.
- **更多:** enterprise logs, login control, authorization management, and secondary management entries.
- **AI:** AI-related configuration or assistant features. Watch permissions, response accuracy, timeout/failure fallback, translation/copy, interaction with existing workflows.

## PRD Scope Routing

For each PRD or commit title, decide the test surface by affected object and runtime, not just by keywords.

- **Management only:** CRUD, lists, forms, filters, permissions, orders, rights, logs, or visible settings that do not affect client local behavior or store runtime.
- **Client required:** local service, local port, kernel, resource package, upgrade, multi-workbench, client settings, cache/download path, process/window state, native integration.
- **Store-inside required:** opening-store chain, environment safety detection/IP network checks, explicit detection pages, store browser behavior, cookie/cache, proxy, plugin runtime, bookmarks, downloads, access-policy execution, supervision capture, page rendering.
- **Ops backend required:** internal admin query/config/migration/monitoring/data operations.
- **Translation required:** any visible page copy is added or changed.
- **Permission required:** roles, custom permissions, authorization, button visibility, data scope, departments/members/roles, or interface authorization changes.
- **Multi-workbench required:** opening-store, local ports/processes, store runtime isolation, account/window state, or any client feature known to interact with multiple workbenches.

When multiple routes apply, include the higher-risk routes, but explain why. Do not add store-inside or client checks just because the product can interact across surfaces.

Boundary tightening is not risk narrowing. First resolve the correct business object and surface, then expand the risk surface according to the requirement's change model. Keep evidence labels explicit so adjacent Bugs help without being presented as direct same-feature history.

For authorization or permission model expansion, intentionally expand beyond same-name Bugs after the object is resolved. This applies when the PRD changes authorization objects, effective members, visible scope, departments, roles, data scope, or shared permission selectors.

Use this expansion for examples such as `授权成员` becoming `成员/部门/角色`, access-policy effective members changing scope, cloud-number authorization sharing the same selector, or role/department permission scope changes:

- save behavior: editing unrelated fields must not clear or overwrite existing authorization;
- display behavior: selected results, list fields, details, hover, logs, and notifications must show every member/department/role correctly;
- filter/statistics behavior: old member-only filters must not miscount department or role authorization;
- hierarchy behavior: department child selection, no-permission child departments, and cancel/current/all-children choices must be distinct;
- role behavior: role name, icon, hover details, and role data scope must not display as ID, blank, or wrong source;
- permission behavior: current user can only see/select authorized members, departments, and roles; check both over-permission and under-permission;
- disabled/deleted object behavior: selected disabled members or removed objects need clear fallback display and must not silently disappear unless the PRD says so;
- shared component behavior: every business entry that reuses the selector should be checked for consistent UI and no unintended regression.

For list, filter, or field model expansion, intentionally expand to list/detail consistency, filter/search/sort/pagination, exports, permission visibility, empty/historical data, refresh/relogin/reopen behavior, and old logic that may still assume the previous field or single-object model.

For state or lifecycle changes, keep the expansion lighter but do not omit it: check status after operation, refresh/relogin/reopen, logs/notifications, permission visibility, failure/cancel/retry/repeat operations, and historical data compatibility.

For client low-level or runtime-chain PRDs, intentionally expand the route along the chain instead of treating the keyword as a single isolated feature. This applies to local ports, kernel, resource packages, cache/download paths, upgrades, multi-workbench, opening-store, local service startup, and client-kernel communication.

Use this expansion only when the changed capability plausibly supports the chain:

- local-port changes can affect opening-store, client-kernel communication, URL launch, multi-workbench isolation, process/port release, and local access restrictions.
- kernel changes can affect opening-store, headless mode, developer tools, plugins, bookmarks, downloads, detection pages, and platform page rendering.
- resource package or upgrade changes can affect startup, cache compatibility, version prompts, client settings, and first launch after upgrade.
- cache/download path changes can affect path conflicts, cleanup safety, opening-store cache, kernel download/unzip resources, and restart recovery.

Keep the output evidence-labeled. Do not use this chain expansion to blur business concepts such as login account versus store account or cloud-number management versus store runtime.

## Evidence Strength

Use these rules to decide whether a historical Bug is direct evidence or only an adjacent reminder.

- **Strong evidence:** same business object, same module/entry, same field/interface/state transition, or same execution-chain failure point.
- **Strong evidence:** same permission scenario and same failure type, such as button visible but interface denied, permission assigned but not effective, permission not assigned but operation succeeds, or data-scope leakage.
- **Medium evidence:** same interaction pattern but different module, such as search/filter/pagination/export/import/batch operation.
- **Medium evidence:** same surface but different module, such as management-system permission/list Bugs reused as adjacent risk for another management-system module.
- **Medium evidence:** adjacent chain node where the PRD plausibly affects the chain, such as local-port changes affecting opening-store communication.
- **Medium-to-strong chain evidence:** adjacent client runtime node where the changed low-level capability is a dependency, such as local-port changes affecting URL launch, multi-workbench process residue, opening-store queue blocking, client-kernel communication, or port release.
- **Medium-to-strong model evidence:** adjacent model node where the changed object model is a dependency, such as authorization expanding from members to departments/roles and therefore affecting hierarchy, role display, data scope, filters, logs, notifications, or shared selector entries.
- **Not direct evidence:** same keyword but different business object, such as `账号中心` versus `账号列表`.
- **Not direct evidence:** same function name on different surface when runtime differs, such as management page copy versus store-inside browser behavior.
- **Old version handling:** permission, data, interface, authorization, cookie isolation, and state-consistency Bugs keep normal reference weight when the core logic is unchanged. UI interaction, old-kernel-specific, V5-only, or rebuilt-module Bugs should be downgraded or ignored when the current PRD is on a redesigned surface or different kernel.

## Useful Examples

- **账号中心账号设置:** route to Ziniao login/member account. Watch login-account permissions, button visibility versus interface authorization, phone/binding/security-center flows, and error prompts. Do not cite store-account authorization Bugs as direct evidence.
- **账号列表 / 店铺账号 authorization:** route to 账号管理 store/platform account management. Watch authorization relationship, store-account list/detail, filters, logs, escrowed credentials, main/additional account behavior. For 附加账号, remember it reuses the main account device environment.
- **账号授权成员扩展为成员/部门/角色:** route to 账号管理 store/platform account authorization. Treat it as authorization-model expansion: keep direct account-authorization Bugs first, then add department hierarchy, role display, data scope, disabled/deleted object fallback, logs/notifications, and shared selector regression for cloud-number authorization and access-policy effective members.
- **云号购买:** route to management-system cloud-number and service/payment/order state. Do not default to opening-store, kernel, proxy, cookie, or IP detection.
- **书签:** route to 店铺内. Watch store isolation, persistence after close/reopen, folder/link operations, Firefox/Chrome kernel behavior if relevant, and multi-workbench isolation.
- **本地端口兜底:** route to client local service plus opening-store/client-kernel communication. Watch port occupied/unavailable, fallback allocation, release after close/exit, multi-workbench isolation, stale callers using old ports, and user-facing failure prompt.
- **访问策略 template or execution:** route to management-system configuration plus store-inside execution. Configuration is expected to affect subsequent access without reopening the store in at least some policy flows; for an already-open store, verify refresh, navigation, and new requests separately from content that was already loaded. Bug `6935388416` directly supports real-time restoration when an access exception expires, but it does not prove that every policy type uses the same propagation mechanism. Watch page/element blocking, role/member/dept scope, and conflicts with custom policy. Do not treat supervision logs as direct evidence unless the PRD mentions them.
- **事中监管 screenshot/log/alert:** route to supervision. Watch capture completeness, screenshot timing/quality, alert triggers, log permissions, performance, and store-window isolation. Do not treat access-policy blocking as direct evidence unless the PRD crosses both.

## Pending Confirmation

Keep these as tentative until the user confirms them; do not write them as strong rules in answers.

- The exact propagation mechanism for each access-policy type in an already-open store. At least the access-exception expiry flow is expected to restore restrictions in real time (`6935388416`), but whether other policy edits use push, refresh, navigation, or the next network request still needs type-specific verification.
- Exact internal 运维后台 module ownership and user-side impact for each ops configuration. Public help documents do not cover 运维后台.
- Exact components of public phrases such as "三重安全检测" unless a current PRD or official document names the components.

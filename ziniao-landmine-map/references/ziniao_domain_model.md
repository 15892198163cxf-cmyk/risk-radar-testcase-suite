# Ziniao Domain Model

Use this reference when turning historical Bugs into supplemental testing advice.

## Product Structure

- 紫鸟整体是一个客户端产品。
- 管理系统 is an online page opened inside the Ziniao client, not a separate native client surface.
- 店铺内 is an isolated browser environment created by an independent browser kernel for each store/account.
- 管理系统, 客户端 shell, and 店铺内 can interact, but they are not interchangeable "multiple terminals".

## Account Terminology

Ziniao has two different account concepts that must not be mixed:

- **紫鸟账号 / 登录账号:** `账号中心`, `账号设置`, `紫鸟账号`, `登录账号`, `成员账号`, `手机号`, `绑定管理`, `安全中心`, and company-login identity. These belong to the user's Ziniao login/member identity.
- **店铺账号 / 平台账号:** `账号列表`, `账号管理`, `编辑账号`, `授权成员`, `托管账密`, `附加账号`, `主账号`, and ecommerce-platform store accounts. These belong to store/platform account management.
- **附加账号:** has its own login credentials, but reuses the main account's bound device environment. Treat its network, IP/proxy, fingerprint/security environment, and store runtime as following the main account unless the requirement says otherwise.

When the request says `账号中心` or `账号设置`, default to 紫鸟账号 / 登录账号. Do not apply 店铺账号 Bugs such as `账号列表`, `编辑账号`, `授权成员`, `托管账密`, or `附加账号` unless the requirement explicitly mentions store/platform accounts.

When the request says `账号列表`, `账号管理`, `店铺账号`, `电商平台账号`, `授权成员`, or `托管账密`, default to 店铺账号 / 平台账号.

If a request only says `账号` and both meanings are plausible, state the ambiguity and resolve from nearby words before citing evidence. It is better to say the evidence boundary is unclear than to use true Bugs for the wrong account type.

## Official Management-System Modules

Use the official module names when routing a PRD, while still checking the actual PRD wording and Bug details:

- **账号管理:** store/platform account management, including add/edit/delete/authorize store accounts, bind devices, and open accounts.
- **设备管理:** purchase devices, add/import self-owned devices, manage devices, bind/unbind devices, and renew devices.
- **云号管理:** purchase cloud numbers, manage cloud numbers, view cloud records, authorize members, and bind cloud numbers to store/platform accounts for usage records.
- **安全监管:** access policy, supervision, webpage resource management, screen watermark, supervision logs, risk-control logs, upload logs, and permission logs.
- **费用管理:** recharge, balance details/export, orders, cloud-number paid services, invoices, and fee summaries. Renewal entries may live in device/cloud-number modules, but fee/order consistency belongs here.
- **企业管理:** member management, department management, role/permission management, certification, enterprise settings, and app management.
- **紫鸟账号中心:** enterprise info, login methods, account security, notification management, phone/binding/security-center flows.
- **更多:** enterprise logs, login control, authorization management, and other secondary management entries.

## Inference Rules

- For 管理系统 purchase, order, billing, membership, or cloud-number management flows, the default post-action visibility check is 管理系统 list/detail/status/rights/order visibility.
- Do not infer "管理系统购买后，客户端/店铺内是否同步看到状态" unless the requirement explicitly says the purchased result affects client shell behavior, store startup, browser runtime, local resources, plugins, account launch, or store isolation.
- For 店铺内 checks, focus on the isolated browser kernel environment: startup, account login, cookies/storage, plugins, proxy/IP, bookmarks, downloads, security policy, and runtime state.
- For 客户端 shell checks, focus on client settings, multi-workbench behavior, resources, upgrades, local cache, window state, launch, and native integrations.
- For 管理系统 checks, focus on online page data: list/detail consistency, permissions, orders, rights, filters, forms, operation logs, and backend state.

## Store Opening, IP Detection, and Local Ports

- `打开店铺` is a store-runtime chain. At the business level, require valid account permission, a resolvable store environment, a usable kernel, a usable device/network route, and target-site reachability.
- `IP检测` is not only a user-opened detection page. Opening the account browser enters environment-safety and network validation before normal site access, and the store/device detection page is another explicit place to inspect results. Do not infer that every device type or every launch calls the same IP-detection interface unless the current diff, trace, or Bug evidence proves it.
- Proxy is conditional on device type; local devices may use the current machine network. Existing cookies/session data and escrowed credential autofill matter when present, but cookie import/export/cleanup is not an unconditional launch step. Cache may be used during browsing, but cache validation or cleanup is not a default launch gate.
- Only add plugin loading, access-policy execution, supervision capture, bookmarks, downloads, or special cache checks when the requirement touches those configured capabilities. Treat local service, local ports, and process reuse as implementation dependencies only when the current change or evidence connects them to the store-opening failure.
- `本地端口` mainly supports opening stores and client-to-kernel communication. For local-port changes, focus on port occupancy, fallback allocation, port release after close/exit, multi-workbench isolation, and whether kernel/client callers switch to the new port.
- `多开工作台` mainly affects opening stores. The core rule is that accounts opened in different workbenches must not affect each other, including port allocation, process state, cookies/proxy state, and store runtime state.

## Device Model

- A device is the configuration/resource unit that provides the store account's network environment and security environment.
- A store/platform account binds a device; the device determines the network exit/proxy IP and browser fingerprint/security environment used when opening the store.
- Device types include Ziniao-provided devices, imported self-owned devices such as proxy devices/VPS/broadband devices, and local/local-dynamic devices using the current machine network.
- Proxy is part of the device network configuration. Remote desktop capability is optional; imported VPS devices may only provide proxy capability.

## Cloud Number Boundary

Do not connect 云号 testing to 打开店铺 by default. Treat `云号购买`, `云号列表`, `云号授权`, `云号替换`, and other cloud-number management flows as normal 云号 test points inside their own management chain unless the requirement explicitly says a cloud number is used by store launch/runtime.

Cloud numbers have two independent relationship dimensions:

- **授权成员:** the authorized member can manage the number and view related SMS/call records.
- **绑定账号:** the cloud number is bound to a store/platform account to record which account uses the number.

## Security Module Terminology

- `事中监管`, `添加监管账号`, and `告警方案` belong to the supervision/监管 capability family.
- `访问策略` and `会员安全策略` belong to the access-policy capability family.
- These families are related through permissions and controlled objects, but do not merge their historical Bugs unless the requirement crosses both families.
- Access-policy configuration is expected to take effect for subsequent access without reopening the store in at least some flows. Bug `6935388416` specifically expects an already-open store to restore restrictions in real time when an access exception expires. Test already-loaded content separately from refresh, navigation, and new network requests, and do not generalize that one propagation mechanism to every policy type without evidence.
- 事中监管 mainly targets store-account/store-operation supervision. Management-system login, configuration, member, account, role, and permission changes belong to their corresponding login/operation/permission logs; the fact that a permission log may appear in the broader security area does not make those management operations part of supervision capture.

## Permission Model

Common roles include BOSS, 超级管理员, 管理员, and 普通成员. BOSS is the enterprise creator with all management permissions. 超级管理员 has broad enterprise-management permissions. 管理员 usually has partial management permissions such as department/account management. 普通成员 usually has partial account/device/cloud-number permissions. Except for BOSS, roles can have customized permissions. Permission-related radar should especially check both under-permission and over-permission: assigned permissions not taking effect, unassigned permissions becoming available, button visibility inconsistent with interface authorization, and role/department data-scope leakage.

## Client Settings

Client settings include browser preferences, startup behavior, window size, page zoom, language switch, notification settings, account file download settings, cache management, terminal information, version/upgrade detection, multi-workbench, and advanced line configuration.

Kernel download is a client capability, but its user entry is usually triggered when opening an account whose specified kernel is not downloaded. Do not assume kernel download belongs to the settings page unless the requirement says so.

## Translation Rule

Any visible page copy needs English translation as a testing rule because the client supports Chinese/English switching. This applies across management pages, client pages, store pages, official/safety pages, and plugin pages when the copy is visible to users, including buttons, labels, prompts, error messages, empty states, and dialogs.

## Feishu Module Reliability

Feishu `所属模块` may be imprecise. Use the title, reproduction steps, failure, expected result, and fix plan to decide the true business concept. Do not rely on module labels alone when choosing evidence.

## Correct Example

When testing 云号购买 in 管理系统:

- Check whether 管理系统 can see the purchased cloud-number state in relevant list/detail/order/rights pages.
- Check payment/order/status/rights consistency inside 管理系统.
- Add 客户端 or 店铺内 checks only if the purchased cloud number is used to launch, bind, or affect a store/browser runtime.

## Incorrect Pattern

Do not write: "管理系统购买后，客户端/店铺内是否同步看到云号状态" as a default supplemental check.

Do not use 店铺账号 evidence for 紫鸟账号 settings. For example, `账号中心/账号设置/移除授权接口权限依赖` should recall 紫鸟账号 Bugs such as login-account permissions, button visibility, phone/binding/security-center behavior, and error prompts. It should not lead with `账号列表/编辑账号/授权成员` store-account Bugs.

Do not write 云号 checks as `打开店铺` checks unless the requirement explicitly connects cloud numbers to store launch/runtime.

Do not place IP detection in 管理系统 by default. It belongs to the store-opening/device-network environment chain, with automatic launch-time environment safety detection and explicit store/device detection-page checks.

Do not guess the exact components of public claims such as "三重安全检测" unless the current requirement or product document names them.

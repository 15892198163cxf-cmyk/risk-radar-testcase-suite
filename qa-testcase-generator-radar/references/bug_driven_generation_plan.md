# 缺陷驱动用例生成方案（无 version_scope 强依赖）v0.1

## 1. 目标

将 `qa-testcase-generator-radar` 从“仅保留 `history_bug: true` 标记”升级为“缺陷驱动生成”：

1. 同时支持两类缺陷：`history_bug` 与 `online_bug`。
2. 关联判断以“模块+功能内容+影响链路”为主，不依赖版本区间。
3. 每条命中缺陷不只生成复现用例，还要生成辐射回归用例（1+N）。
4. 交付前必须输出“缺陷覆盖矩阵”。

---

## 2. 缺陷分层定义

### 2.1 history_bug
- 含义：历史出现并已修复的缺陷，主要用于防回归。
- 默认策略：命中关联时纳入必测；未命中时按风险抽测。

### 2.2 online_bug
- 含义：线上高风险缺陷（影响用户/业务/稳定性）。
- 默认策略：命中关联即强制覆盖，且测试密度高于 history_bug。

### 2.3 分层建议（当前可执行）
- 满足任一条件可标为 `online_bug`：
  - 优先级为高；
  - 缺陷分类含“线上缺陷”；
  - 严重度较高且有客户可见影响。
- 其余标为 `history_bug`。

### 2.4 往期用例导入口径（你当前真实规则）
- 来源：往期用例导入时的 `测试结果` 字段。
- 规则：
  - `测试结果 = N` -> 视为历史缺陷，标记 `history_bug`。
  - `测试结果 = Y` -> 视为通过记录，不标记 `history_bug`。
- 备注：
  - 该规则用于“历史缺陷识别”。
  - `online_bug` 仍由飞书线上缺陷池单独标注，不与 `Y/N` 混用。

---

## 3. 输入数据规范（适配飞书现有字段）

> 说明：只使用你当前飞书页面可获取字段。没有 `bug_id` 时自动生成 `bug_key`。

```yaml
bug_key: "sha1(标题+开始时间+所属模块)"   # 自动生成唯一键
bug_tier: online_bug | history_bug
source: feishu

title: "【静默升级】V6版本配置客户端静默升级后，启动客户端，精简面板会白屏一直加载"
status: Closed
start_time: "2026-03-25"
priority: 高
severity: 一般
defect_type: 代码错误
defect_category: "线上缺陷/V6客户端"
module: 客户端
related_version_text: "速留缺陷&线上问题"   # 原样保留文本

repro_steps: |
  1. V6版本配置客户端静默升级后，启动客户端
actual_result: "精简面板会白屏一直加载"
expected_result: "正常加载"

tags:
  scene: "客户端启动/首页加载"
  trigger: "静默升级后首次启动"
  failure_pattern: "白屏+持续loading"
  root_cause_tag: "upgrade_init"   # 初期可人工标注：upgrade_init/config_parse/cache_state/permission/render/api
```

---

## 3.1 历史导入字段映射（Y/N -> 缺陷标签）

```yaml
import_source: testcase_excel
test_result: N

# 导入后标准化结果
bug_tier: history_bug
history_bug: true
history_bug_source: "legacy_test_result_N"
```

映射规则：
1. `test_result=N`：生成或更新对应用例的 `history_bug: true`。
2. `test_result=Y`：不自动打 `history_bug`（如已有人工标记，不主动清空）。
3. 同一用例后续又出现 `N`：累计 `recurrence_count +1`（用于风险提权）。

---

## 4. 关联匹配规则（核心）

## 4.1 匹配输入
- 当前需求分析结果中的：模块、功能点、场景、操作、关键字段、上下游模块。
- 缺陷库中的：`module`、`title`、`defect_type`、`tags.*`、`repro_steps`。

## 4.2 打分模型（v1）
- 模块精确命中：+40
- 场景关键词命中（scene/title/repro）：+25
- 缺陷类型命中（如代码错误/权限/接口）：+15
- 触发条件或失败现象命中：+15
- 上下游链路命中：+10

## 4.3 分档策略
- `score >= 60`：`must_cover`（必测）
- `40 <= score < 60`：`should_cover`（建议覆盖）
- `< 40`：`reference_only`（仅参考）

## 4.4 online_bug 强化规则
- `online_bug` 且 `score >= 50` 直接提升为 `must_cover`。

---

## 5. 1+N 用例扩写策略（不是只写复现）

对每条 `must_cover` 缺陷，至少生成以下用例组：

1. **R-复现用例（1条）**
   - 原始步骤高保真复现。

2. **V-同场景变体（2-3条）**
   - 同路径不同状态：首次启动/二次启动、清缓存后启动、登录态变化等。

3. **C-同根因变体（2-3条）**
   - 例如 `upgrade_init`：升级中断、配置缺失、旧配置残留、弱网初始化。

4. **U-上下游联动（1-2条）**
   - 与该模块有数据/状态交互的关联模块回归。

5. **G-保护性用例（1条）**
   - 防“修复引入新问题”的守护用例（最小回归护栏）。

### 密度建议
- `online_bug`：每条至少 6-10 条（R+V+C+U+G）
- `history_bug`：每条至少 3-6 条（R+V+G，按风险补 C/U）

---

## 6. 映射到现有 Skill 流程

## 6.1 Step 3（知识库命中）
从“仅扫描 `history_bug: true`”改为：
1. 加载缺陷池（history+online）。
2. 运行匹配打分，产出：
   - `must_cover_bug_list`
   - `should_cover_bug_list`

## 6.2 Step 4/5（交叉分析与生成策略）
交叉分析时确认缺陷是否适用，并在生成策略中输出 `must_cover_bug_list`：
1. 每个 `must_cover` 执行 1+N 扩写。
2. 新生成用例追加：
   - `history_bug: true`
   - `history_bug_source: feishu`
   - `source_bug_keys: [bug_key]`
   - `bug_tier: online_bug/history_bug`

## 6.3 Step 7（自审）
新增强制输出“缺陷覆盖矩阵”（见第 7 节模板）：
- 任一 `online_bug` 未覆盖 => 自审不通过。

## 6.4 Step 9（归档）
归档时保存覆盖快照，供下次增量生成复用：
- `bug_key -> testcase_ids -> covered_at`

---

## 7. 自审输出模板（强制）

```markdown
## 缺陷覆盖矩阵
| bug_key | bug_tier | 模块 | 匹配分 | 覆盖用例ID | 状态 | 备注 |
|---------|----------|------|--------|------------|------|------|
| ...     | online_bug | 客户端 | 78 | TC-012,TC-013,TC-021 | ✅已覆盖 | 含复现+根因变体 |
| ...     | history_bug | 客户端 | 63 | TC-030,TC-031 | ✅已覆盖 | 含复现+保护用例 |

## 未覆盖清单
- bug_key=...（online_bug）=> 阻断交付，必须补齐
```

---

## 8. 示例（基于“静默升级后白屏loading”）

## 8.1 缺陷入池（摘要）
- `module=客户端`
- `scene=客户端启动/首页加载`
- `trigger=静默升级后首次启动`
- `failure_pattern=白屏+持续loading`
- `bug_tier=online_bug`

## 8.2 预计生成用例（示例）
1. 复现：静默升级后首次启动，验证不再白屏。
2. 变体：升级后二次启动，验证首页可稳定进入。
3. 变体：升级后清缓存再启动，验证配置兼容。
4. 根因：升级后配置缺失/空值，验证容错与降级。
5. 根因：弱网下启动，验证超时与重试策略。
6. 根因：旧配置残留场景，验证迁移逻辑。
7. 联动：启动成功后首页关键接口加载链路验证。
8. 保护：修复后启动性能与首次渲染时长不劣化（基础阈值）。

---

## 9. 渐进落地计划（建议）

1. 第一阶段（1周）
   仅新增字段和覆盖矩阵，不改现有导出脚本。

2. 第二阶段（1-2周）
   将最近3个月飞书缺陷入池，先覆盖高频模块。

3. 第三阶段（持续）
   每次生成自动补全 `source_bug_keys`，逐步替换粗粒度 `history_bug: true`。

---

## 10. 不做项（当前版本）

1. 不强制依赖 `version_scope`。
2. 不要求飞书必须提供标准 `bug_id`（用 `bug_key` 过渡）。
3. 不要求一次性清洗全部历史 YAML，仅按新生成和高频模块增量修复。

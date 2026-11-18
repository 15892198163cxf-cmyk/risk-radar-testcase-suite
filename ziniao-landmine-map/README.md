# Ziniao Landmine Map

紫鸟测前风险雷达。开始测试或编写用例前，从历史线上 Bug、测试经验、业务规则和历史用例中召回与当前需求真正相关的风险，并给出简洁、可执行的检查点。

## 适用场景

- 测试紫鸟客户端、管理系统、店铺内、运维后台、移动端、内核、账号、设备、云号或安全相关需求前，想先了解历史雷区。
- 需求是旧功能改动，需要找同功能或同链路的历史复发风险。
- 需求是新功能，需要从同模块、同数据模型、权限、状态或运行链路推导易漏风险。
- 想确认历史 Bug、测试经验或已有业务规则是否会影响本次测试范围。
- 只需要“风险 + 证据 + 测试点”，暂时不需要完整测试用例。

## 不适用场景

- 需要直接生成完整测试用例时，使用 `risk-radar-testcase-workflow`，由它把雷达结果交给 `qa-testcase-generator`。
- 不需要历史风险增强，只想按 PRD 生成普通用例时，直接使用 `qa-testcase-generator`。
- 已经有测试用例，只需要检查覆盖率和质量时，使用 `qa-testcase-reviewer`。
- 需要执行真实接口、安全测试或输出接口报告时，使用 `api-security-tester`。

## 常见触发话术

- 使用 `$ziniao-landmine-map` 分析这份需求的历史雷区。
- 帮我看看账号锁定审批功能以前踩过哪些坑。
- 这个新功能测试前有哪些高风险点容易遗漏？
- 只做测前雷达，不用生成完整测试用例。
- 结合历史线上 Bug，给我可执行的测试提醒。

## 输入材料

- PRD、飞书需求、Markdown、PDF、图片或粘贴的需求文本。
- 测试目标，例如管理系统、客户端、店铺内、运维后台或移动端。
- 可选：说明是新功能还是旧功能改动；未说明时会根据需求文字保守判断。
- 可选：明确关注的角色、状态、数据范围、版本、入口或运行环境。

## 输出结果

- 需求识别和本次重点关注的变化模型。
- 与当前需求直接相关或强相关的历史 Bug 风险。
- 有条件才成立的相邻风险，并明确适用条件。
- 基于需求和测试经验推导的易漏风险。
- 每项风险对应的简洁、可执行测试点。
- 证据来源、适用边界、无匹配或数据不可用说明。
- 会实质影响测试设计的待确认问题。

雷达默认不输出完整用例 ID、详细前置条件、逐步操作和预期结果。如果需要完整用例，应改用 `risk-radar-testcase-workflow`。

## 使用示例

### 只分析历史风险

```text
使用 $ziniao-landmine-map 分析这份账号锁定申请审批需求。
这是旧功能改动，只输出历史风险、证据和测试点，不生成完整用例。
```

### 分析新功能易漏点

```text
使用 $ziniao-landmine-map 分析运维后台新增抖店实物订单发券功能。
这是新功能，请区分历史证据和测试推导，并标出待确认项。
```

### 继续生成完整用例

如果目标是最终生成用例，不要先单独执行一次雷达再手工复制结果，直接使用：

```text
使用 $risk-radar-testcase-workflow，先分析这份需求的风险，再按详细模式生成测试用例并导出 Excel。
```

## 与其他 Skill 的关系

| Skill | 什么时候使用 |
| --- | --- |
| `ziniao-landmine-map` | 只做紫鸟测前风险分析。 |
| `risk-radar-testcase-workflow` | 需要雷达增强后的完整测试用例。 |
| `qa-testcase-generator` | 不使用雷达，直接按需求生成普通测试用例。 |
| `qa-testcase-reviewer` | 已有用例，需要独立评审质量。 |

## 数据来源与边界

- 仓库保存 Skill 源码、静态规则、测试经验种子和最小脱敏回归夹具。
- `data/normalized_bugs.jsonl` 是从 `viking://resources/ziniao-online-bugs-governed` 同步的本地受治理镜像，不提交到 Git。
- `data/feishu_raw/`、聚类文件、场景索引和失败备份都是运行时数据，不提交到 Git。
- OpenViking 远端不可用时，只能使用已有的已验证缓存和仓库种子，并明确说明 `local_fallback`。
- 历史 Bug 证明问题发生过，但不能单独定义当前需求的正确业务规则。
- 默认只读；未经用户明确确认，不回写飞书或修改远端知识数据。

## 首次同步

在 Skill 根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/refresh_openviking_bug_cache.ps1
```

同步需要环境变量 `OPENVIKING_KNOWLEDGE_PLUGIN_USER_KEY`。没有凭据或远端不可用时，脚本会安全降级，不覆盖现有缓存。

## 维护验证

```powershell
py -m unittest discover -s scripts -p "test_*.py"
py scripts/landmine.py eval --limit 20
py scripts/landmine.py radar-eval
```

后两项完整回归依赖已同步的线上缺陷镜像和生成索引；单元测试使用隔离夹具，不依赖开发机缓存。

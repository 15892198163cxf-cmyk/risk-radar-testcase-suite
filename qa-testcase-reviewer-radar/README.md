# QA Testcase Reviewer Radar

`risk-radar-testcase-workflow` 专用的雷达增强用例评审器。它在完整用例生成后，对照需求、规范 `radar_result` 和最终 `radar_impact` 检查覆盖、追溯、粒度和导出准备度。

## 使用边界

- 仅由 `risk-radar-testcase-workflow` 显式调用，不参与普通评审请求的自动匹配。
- 普通、不使用雷达的用例评审继续使用 `qa-testcase-reviewer`。
- 先输出有证据的评审结论；只有工作流或用户明确要求修复时才修改用例。

## 输入材料

- 当前需求与生成模式。
- `qa-testcase-generator-radar` 产出的最终候选用例。
- 同一次运行的规范 `radar_result` 与用例中的 `radar_impact`。

## 重点检查

- 需求映射、矛盾、联动/状态流转和写入—读取闭环。
- 步骤原子性、动作—预期闭环、权限维度和语义重复。
- 雷达风险/测试点是否覆盖、排除或待确认，并正确区分“复核强化”和“新增用例”。
- 用例 ID、来源、计数和 Excel 雷达增益数据是否一致。

## 调用关系

```text
qa-testcase-generator-radar
  -> qa-testcase-reviewer-radar
  -> 用户确认
  -> 一次导出最终 Excel
```

## 维护说明

- 评审规则位于 `references/`。
- 同步普通评审器修复时必须复核差异，不得把雷达门禁写回普通评审器。

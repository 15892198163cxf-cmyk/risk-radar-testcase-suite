# QA Testcase Generator Radar

`risk-radar-testcase-workflow` 专用的雷达增强用例生成器。它接收当前需求及同一次雷达运行产生的规范 `radar_result`，在一套最终用例中合并历史风险、执行质量校验并导出 Excel。

## 使用边界

- 仅由 `risk-radar-testcase-workflow` 显式调用，不参与普通用例请求的自动匹配。
- 普通、不使用雷达的需求继续使用 `qa-testcase-generator`。
- 雷达测试点是高价值分析输入，不直接当作需求事实；未确认规则仍需询问用户。
- 合并已有覆盖，只为仍未覆盖的实质风险新增用例，即“雷达增强，不雷达膨胀”。

## 输入材料

- 当前需求材料和生成模式。
- 同一需求、同一证据快照的规范 `radar_result`。
- 可选：验收标准、原型、接口说明和明确的不覆盖范围。

## 输出结果

- 合并去重后的需求分析、澄清问题和完整测试用例。
- 顶层 `radar_impact` 雷达消费统计。
- 通过质量校验、可交给 `qa-testcase-reviewer-radar` 评审的 JSON/YAML。
- 用户确认后一次导出的 Excel；雷达套件包含 `testcases` 和 `雷达增益` Sheet。

## 调用关系

```text
ziniao-landmine-map
  -> risk-radar-testcase-workflow
  -> qa-testcase-generator-radar
  -> qa-testcase-reviewer-radar
```

如需普通生成，请显式使用：

```text
使用 $qa-testcase-generator 按详细模式分析需求，不使用风险雷达。
```

## 维护说明

- 本目录从普通生成器建立隔离基线，但雷达规则只维护在这里。
- 同步普通生成器修复时必须复核差异，不得反向修改普通生成器来承载雷达字段。
- 规则细节位于 `references/`，确定性校验和导出工具位于 `scripts/`。

# 知识库管理指南

## 知识库目录
知识库目录: `qa-knowledge/`（位于 workspace 根目录）

### 目录结构
```
qa-knowledge/
├── rules/                  # 业务规则文件
│   ├── rule-001.yaml
│   ├── rule-002.yaml
│   └── ...
├── rule-index.yaml         # 规则索引（标题+摘要+关键词）
├── feedback-log.md         # 反馈记录
└── learned-patterns.yaml   # 从反馈中提炼的通用模式
```

### 规则格式
```yaml
rule_id: "unique-id"
title: "规则标题"
summary: "一句话描述"
keywords:
  - "关键词1"
  - "关键词2"
content: |
  详细的业务规则描述。
  包含逻辑、约束、边界条件等。
version: 1
created_at: "YYYY-MM-DD"
updated_at: "YYYY-MM-DD"
```

### 新增规则
1. 创建 `qa-knowledge/rules/rule-NNN.yaml`
2. 更新 `qa-knowledge/rule-index.yaml` 添加索引条目
3. 确认规则内容完整且无歧义

### 查询规则
1. 读取 `rule-index.yaml`
2. 用需求内容与规则的 title + summary + keywords 做语义匹配
3. 相关度高的规则 → 读取完整 content
4. 将规则内容作为上下文注入用例生成

### 从反馈中学习
1. 记录反馈到 `feedback-log.md`
2. 如果反馈是通用规则 → 创建新规则文件
3. 如果反馈是模式优化 → 更新 `learned-patterns.yaml`

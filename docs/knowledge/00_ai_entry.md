---
knowledge_version: 1
project: parse-video-py
project_scale: M
project_type: code
last_scanned_at: 2026-06-08
source_commit: dd55df3
confidence: high
---

# AI 编程助手入口

## 知识库用途

本知识库帮助 AI 编程助手快速理解本项目，稳定修改代码，避免误改核心逻辑。

## 一人公司项目原则

- 优先上线，而不是过度架构。
- 优先简单稳定，而不是技术炫技。
- 优先复用现有模块，而不是新增复杂抽象。
- 优先商业闭环，而不是纯技术完整性。
- 优先小步迭代，而不是大范围重构。
- 优先降低未来维护成本。
- 修改解析器、路由映射、鉴权、部署等核心能力必须谨慎。

## AI 工作规则

- 先读 99_global_index.md，再按任务读取相关文档。
- 没有证据不得臆测项目能力。
- 不确定时必须回到源码、配置、测试或文档中查证。
- 新增代码必须遵守 04_code_rules.md。
- 修改核心逻辑必须读取 05_change_safety.md。
- 能局部修改就不要全局重写。
- 禁止为了"优化"而大范围重构稳定代码。

## 常见任务入口

| 任务 | 必读文档 | 备注 |
|---|---|---|
| 新增平台解析器 | 02_project_map.md、03_core_flows.md、04_code_rules.md | 参考已有解析器模式 |
| 修改解析逻辑 | 03_core_flows.md、05_change_safety.md | 先看影响范围 |
| 新增 API 接口 | 02_project_map.md、03_core_flows.md、04_code_rules.md | 确认路由和响应格式 |
| 修 Bug | 02_project_map.md、03_core_flows.md、06_build_run_deploy.md | 先复现再修复 |
| 修改配置 | 02_project_map.md、05_change_safety.md、06_build_run_deploy.md | 注意环境变量 |
| 部署上线 | 06_build_run_deploy.md | 不要猜部署方式 |

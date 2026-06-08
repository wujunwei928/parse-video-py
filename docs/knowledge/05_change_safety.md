---
knowledge_version: 1
last_scanned_at: 2026-06-08
source_commit: dd55df3
---

# 变更安全规则

## 高风险区域

| 区域 | 路径 | 风险 | 修改前必须检查 | 风险等级 | 证据来源 |
|---|---|---|---|---|---|
| 解析器路由映射 | `parser/__init__.py:video_source_info_mapping` | 影响所有平台的 URL 路由 | 所有平台域名匹配是否正确 | **高** | `parser/__init__.py:29-145` |
| BaseParser 接口 | `parser/base.py:BaseParser` | 影响所有 26 个解析器 | 所有解析器是否兼容新接口 | **高** | `parser/base.py:95-118` |
| 数据结构定义 | `parser/base.py:VideoInfo/VideoAuthor/ImgInfo` | 影响 API 响应格式和所有解析器 | 是否破坏前后端兼容性 | **高** | `parser/base.py:41-92` |
| VideoSource 枚举 | `parser/base.py:VideoSource` | 影响路由映射和 API 参数 | 路由映射和解析器是否同步更新 | **高** | `parser/base.py:9-38` |
| Web 路由和鉴权 | `web.py` | 影响所有 API 接口 | 鉴权逻辑是否正确 | **高** | `web.py` |
| URL 提取工具 | `utils.py:extract_url()` | 影响 URL 解析入口 | 正则表达式是否覆盖所有场景 | 中 | `utils.py:4-10` |
| CLI 命令注册 | `cli/__init__.py` | 影响 CLI 用户 | 命令参数是否向后兼容 | 低 | `cli/__init__.py` |
| CI/CD 配置 | `.github/workflows/` | 影响自动化构建和部署 | 测试和构建流程是否正确 | 中 | `.github/workflows/` |

## 禁止事项

- 禁止一次性大范围重构。
- 禁止删除未知用途代码。
- 禁止未确认调用方就改公共函数签名。
- 禁止把密钥写入代码。
- 禁止为了"看起来更优雅"重写稳定模块。
- 禁止修改 `secrets.compare_digest()` 为普通字符串比较（时序攻击风险）。
- 禁止修改 `video_source_info_mapping` 但不添加对应解析器。
- 禁止修改 `VideoSource` 枚举但不更新映射表。

## 修改前检查清单

- 这个函数被谁调用？（用 Grep 搜索函数名）
- 是否影响解析器路由？（检查 `video_source_info_mapping`）
- 是否影响 API 响应格式？（检查 `VideoInfo` 数据结构）
- 是否影响鉴权逻辑？（检查 `web.py` 的 `_auth_dependency`）
- 是否影响 CLI 命令？（检查 `cli/__init__.py`）
- 是否需要新增或修改测试？
- 是否需要更新知识库？

## 变更影响地图

| 修改内容 | 可能影响 | 必须测试 | 必须同步更新的文档 |
|---|---|---|---|
| 新增/修改解析器 | 路由映射、API 响应 | 对应平台解析测试 | 02_project_map.md、03_core_flows.md、99_global_index.md |
| 修改 VideoInfo 结构 | 所有解析器、API 响应格式 | 全部测试 | 02_project_map.md、03_core_flows.md |
| 修改 video_source_info_mapping | 所有平台 URL 路由 | 路由匹配测试 | 02_project_map.md、03_core_flows.md |
| 修改 BaseParser 接口 | 所有 26 个解析器 | 全部解析器 | 04_code_rules.md |
| 修改 Basic Auth 逻辑 | 所有 API 接口访问 | 鉴权测试 | 03_core_flows.md、05_change_safety.md |
| 新增环境变量 | 部署配置 | 启动测试 | 02_project_map.md、06_build_run_deploy.md |
| 修改部署方式 | Docker 镜像、CI/CD | Docker 构建 | 06_build_run_deploy.md |

## 知识库更新规则

| 代码变更 | 必须更新文档 |
|---|---|
| 新增/删除平台解析器 | 02_project_map.md、03_core_flows.md、99_global_index.md |
| 修改 VideoInfo 数据结构 | 02_project_map.md、03_core_flows.md |
| 修改鉴权逻辑 | 03_core_flows.md、05_change_safety.md |
| 新增环境变量 | 02_project_map.md、06_build_run_deploy.md |
| 新增核心模块 | 02_project_map.md、99_global_index.md |
| 修改部署方式 | 06_build_run_deploy.md |
| 修改代码规范 | 04_code_rules.md |

## 不需要更新知识库的情况

- 单个解析器内部逻辑微调。
- 无业务含义的样式调整。
- 局部 bugfix 且不改变流程。
- 测试用例补充但不改变规则。
- 注释修正。

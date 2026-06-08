---
knowledge_version: 1
last_scanned_at: 2026-06-08
source_commit: dd55df3
confidence: high
---

# 产品上下文

## 项目一句话定位

Python 短视频去水印解析服务，支持 25 个视频平台和 5 个图集平台的分享链接解析，返回无水印视频/图集直链。

- 证据来源：`pyproject.toml:description`、`README.md:6`

## 目标用户

| 用户类型 | 痛点 | 使用场景 | 证据来源 |
|---|---|---|---|
| 开发者 | 需要批量获取视频直链 | API 集成、自动化脚本 | `README.md:159-183`（提供了 SDK 调用示例） |
| AI 工具用户 | 需要 MCP 协议接入视频解析能力 | Claude/其他 AI 工具集成 | `README.md:16-17`（MCP 支持） |
| 普通用户 | 需要去水印下载视频 | Web 界面操作 | `README.md:124`（前端页面） |

## 核心功能

| 功能 | 用户价值 | 当前实现状态 | 入口/路径 | 优先级 | 证据来源 |
|---|---|---|---|---|---|
| 分享链接解析 | 输入分享链接获取无水印视频 | 已实现 | `GET /video/share/url/parse` | P0 | `src/parse_video_py/web.py:75` |
| 视频 ID 解析 | 通过平台+ID 获取视频 | 已实现 | `GET /video/id/parse` | P0 | `src/parse_video_py/web.py:98` |
| 图集解析 | 支持图片图集（含 LivePhoto） | 已实现（5平台） | 同上 | P1 | `src/parse_video_py/parser/base.py:58-67` |
| CLI 命令行 | 本地批量解析 | 已实现 | `parse-video-py parse` | P1 | `src/parse_video_py/cli/__init__.py:24` |
| Web 界面 | 可视化操作 | 已实现 | `GET /` | P2 | `src/parse_video_py/web.py:64` |
| MCP 集成 | AI 工具直接调用 | 已实现 | `GET /mcp` | P2 | `src/parse_video_py/web.py:26-27` |
| Basic Auth | 保护接口安全 | 已实现（可选） | 环境变量控制 | P3 | `src/parse_video_py/web.py:32-57` |

## 商业模式

当前项目为开源工具（MIT 许可证），未发现付费、订阅或商业化功能。

- 证据来源：`LICENSE:MIT`、`README.md`（无 pricing 页面或付费相关内容）

## MVP 边界

**做什么**：短视频/图集分享链接解析，返回标准化的视频信息（URL、标题、作者、封面、音乐）。
**不做什么**：视频下载、视频编辑、用户系统、内容推荐、视频存储。

- 推断依据：`pyproject.toml:description`、`README.md` 功能描述范围、`VideoInfo` 数据结构字段
- 置信度：高

## 产品原则

- 解析优先：核心价值是准确解析出无水印视频直链
- 平台覆盖：支持尽可能多的中文短视频平台
- 标准输出：所有解析器返回统一的 `VideoInfo` 结构
- 图集支持：同时支持视频和图集内容（含 LivePhoto）

## 已支持平台（26 个视频来源枚举）

抖音、快手、皮皮虾、微博、微视、绿洲、最右、度小视、西瓜、梨视频、皮皮搞笑、虎牙、AcFun、逗拍、美拍、全民K歌、6间房、新片场、好看视频、哔哩哔哩、小红书、Twitter/X、腾讯视频、搜狐视频、央视网

- 证据来源：`src/parse_video_py/parser/base.py:9-38`（VideoSource 枚举）

## 未确认事项

- 是否有商业变现计划：未确认
- 用户规模和使用数据：未确认

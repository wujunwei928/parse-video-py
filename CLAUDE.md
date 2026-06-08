# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based video parsing service that extracts video information from multiple Chinese social media platforms. It removes watermarks and provides direct video URLs from 20+ platforms including Douyin, Kuaishou, Weibo, Xiaohongshu, and others.

## Architecture

Source code lives under `src/parse_video_py/` (hatchling build).

- **Web** (`src/parse_video_py/web.py`): FastAPI app, routes, Basic Auth, MCP
- **Parsers** (`src/parse_video_py/parser/`): 26 platform parsers inheriting `BaseParser`
- **CLI** (`src/parse_video_py/cli/`): Typer commands (parse/serve/version)
- **Utils** (`src/parse_video_py/utils.py`): URL extraction, query param parsing

### Core Components

**BaseParser** (`src/parse_video_py/parser/base.py`):
- Abstract base class for all platform parsers
- Defines `VideoSource` enum (26 platforms), `VideoInfo`, `VideoAuthor`, `ImgInfo` dataclasses
- Subclasses must implement `parse_share_url()` and `parse_video_id()`

**Parser Routing** (`src/parse_video_py/parser/__init__.py`):
- `video_source_info_mapping`: VideoSource → domain_list + parser class
- `parse_video_share_url()`: URL → domain match → parser → VideoInfo
- `parse_video_id()`: VideoSource + ID → parser → VideoInfo

## Development Commands

### Local Development
```bash
# Create venv and install all dependencies (Python >= 3.10 required)
uv venv && uv pip install -e ".[all]"

# Install with optional groups
uv pip install -e ".[web]"      # Web server only
uv pip install -e ".[cli]"      # CLI only
uv pip install -e ".[all,dev]"  # With dev tools

# Activate venv
source .venv/bin/activate

# Run development server
uvicorn main:app --reload

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000

# CLI usage
parse-video-py parse "https://v.douyin.com/xxx"
parse-video-py parse "url1" "url2" --format json
parse-video-py parse -f urls.txt
parse-video-py serve --port 8000
```

### Code Quality
The project uses pre-commit hooks with formatting tools:
- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (black-compatible profile)
- **flake8**: Linting (max line length: 88)

```bash
# Install pre-commit hooks
pre-commit install

# Run formatting tools manually
black .
isort .
flake8 .
```

**Note**: The actual flake8 configuration in `.pre-commit-config.yaml` shows max line length as 88, but some development uses 79. Follow existing patterns in each file.

### Testing
The project uses pytest with pytest-asyncio (`asyncio_mode = "auto"` in `pyproject.toml`):

```bash
# Run all tests
pytest tests/ -v --tb=short

# Run specific test files
pytest tests/test_main.py         # API endpoint tests
pytest tests/test_cli.py          # CLI command tests
pytest tests/test_utils.py        # Utility function tests
pytest tests/test_new_parsers_routing.py  # Parser routing tests
pytest tests/test_cctv.py         # Platform-specific parser tests
pytest tests/test_qqvideo.py
pytest tests/test_sohu.py
pytest tests/test_twitter.py

# Run tests with coverage
pytest --cov=parse_video_py
```

### Docker
```bash
# Build and run
docker run -d -p 8000:8000 wujunwei928/parse-video-py

# Run with basic auth
docker run -d -p 8000:8000 -e PARSE_VIDEO_USERNAME=username -e PARSE_VIDEO_PASSWORD=password wujunwei928/parse-video-py
```

## API Endpoints

- `GET /`: Web interface
- `GET /video/share/url/parse?url=<share_url>`: Parse video from share URL
- `GET /video/id/parse?source=<source>&video_id=<id>`: Parse video by ID
- MCP endpoint: `http://localhost:8000/mcp` (via FastAPI-MCP in `web.py`)

### Basic Auth
Set environment variables to enable (unset = disabled):
```bash
export PARSE_VIDEO_USERNAME=username
export PARSE_VIDEO_PASSWORD=password
```

## Important Notes

- All parsers must handle both share URLs and video IDs
- Default UA: `fake_useragent.UserAgent(os="iOS").random` (some parsers use `os="windows"`)
- Video URLs should be direct, watermark-free when possible
- 26 platforms support video, 5 also support image albums (Douyin, Kuaishou, Xiaohongshu, Pipixia, Weibo)
- LivePhoto support: Douyin and Xiaohongshu
- Image parsers should prioritize highest quality: large > original > bmiddle > url
- Use app share links when possible; desktop web versions may not be fully tested
- Auth uses `secrets.compare_digest()` — do not replace with plain string comparison
- Platform-specific details (Douyin Live Photo, Weibo album, etc.) → see `docs/knowledge/03_core_flows.md`

## Adding New Platforms

1. Create `src/parse_video_py/parser/<name>.py` inheriting from `BaseParser`
2. Add enum value to `VideoSource` in `base.py`
3. Update `video_source_info_mapping` in `parser/__init__.py` with domain list and parser class
4. Implement `parse_share_url()` and `parse_video_id()`
5. Add tests in `tests/test_<name>.py`
6. Update knowledge base: `02_project_map.md` + `99_global_index.md`

## Direct Parser Usage

```python
import asyncio
from parse_video_py import parse_video_share_url, parse_video_id, VideoSource

# Parse from share URL
video_info = asyncio.run(parse_video_share_url("share_url"))

# Parse from video ID
video_info = asyncio.run(parse_video_id(VideoSource.DouYin, "video_id"))
```

## Agent skills

### Issue tracker

Issues live in GitHub Issues for this repo. Use the `gh` CLI for all operations. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the default five-role triage label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo. Domain glossary at `CONTEXT.md` and ADRs at `docs/adr/` in the repo root. See `docs/agents/domain.md`.

---

## AI 知识库使用规则（强制）

> **IMPORTANT**: 本项目有 AI 编程知识库。任何代码修改前，必须先读取知识库中的相关文档。这不是建议，是硬性规则。违反此规则可能导致误改核心逻辑、破坏现有功能。

### 知识库位置
- 项目知识库：`docs/knowledge/`
- **入口文件（必读）**：`docs/knowledge/00_ai_entry.md`
- **全局索引（必读）**：`docs/knowledge/99_global_index.md`

### 强制工作流

**每次接到任务时，执行以下步骤：**

1. **先读** `docs/knowledge/99_global_index.md`，根据任务类型确定需要读哪些文档
2. **再读**对应文档，理解相关流程和约束
3. **然后**才开始编写或修改代码
4. **最后**判断是否需要更新知识库

跳过步骤 1-2 直接修改代码是**被禁止的**。

### 按任务类型的必读文档

| 任务类型 | 必须先读 | 原因 |
|---|---|---|
| 新增平台解析器 | 全局索引 → 核心流程 → 编码规则 | 确认解析器模式和路由注册 |
| 修改解析逻辑 | 全局索引 → 核心流程 → 变更安全 | 确认影响范围 |
| 修改鉴权 | 全局索引 → 变更安全 | Basic Auth 高风险区域 |
| 新增接口 | 全局索引 → 核心流程 → 编码规则 | 确认路由和响应格式 |
| 修 Bug | 全局索引 → 核心流程 | 理解上下文再修复 |

### 高风险修改约束

修改以下区域前**必须阅读变更安全文档**，否则禁止修改：
- 解析器路由映射（`video_source_info_mapping`）
- BaseParser 接口和数据结构（`VideoInfo`、`VideoSource`）
- Web 鉴权逻辑
- 部署配置/CI/CD

禁止事项：
- 禁止一次性大范围重构稳定代码
- 禁止删除未知用途代码
- 禁止未确认调用方就改公共函数签名
- 禁止把密钥写入代码

### 变更后知识库维护

代码发生以下变更后，必须同步更新对应的知识库文档：
- 新增/删除解析器 → 项目地图 + 核心流程 + 全局索引
- 修改 VideoInfo 结构 → 项目地图 + 核心流程
- 修改鉴权逻辑 → 核心流程 + 变更安全
- 新增环境变量 → 项目地图 + 构建部署 + 变更安全
- 修改部署方式 → 构建部署 + 变更安全

### 不需要更新知识库的情况
- 单个解析器内部逻辑微调
- 无业务含义的样式调整
- 局部 bugfix 且不改变流程
- 测试用例补充但不改变规则

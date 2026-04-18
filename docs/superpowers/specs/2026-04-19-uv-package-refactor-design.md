# 设计文档：uv 包管理 + 双模式项目改造

> 日期：2026-04-19
> 状态：已确认

## 背景

将 parse-video-py 项目从传统的 `venv + requirements.txt` 模式迁移到 `uv` 包管理，并将项目改造为既可以启动 Web 服务，也可以作为 Python package 安装使用，同时提供 CLI 命令行工具。

## 目标

1. 使用 uv 创建虚拟环境和包管理
2. 项目可通过 `pip install -e .` 或 `uv pip install -e .` 安装为 package
3. 提供三种使用方式：Python API、CLI 命令行、Web 服务
4. CLI 命令对齐 Go 版（parse-video）的命令结构

## 改造方案：src 标准布局

### 目录结构

```
parse-video-py/
├── pyproject.toml                     # uv 项目配置 + 包元数据
├── uv.lock                            # uv 锁文件（自动生成）
├── src/
│   └── parse_video_py/
│       ├── __init__.py                # 公开 API 导出
│       ├── base.py                    # VideoInfo, VideoSource, BaseParser
│       ├── parser/                    # 各平台解析器
│       │   ├── __init__.py            # video_source_info_mapping + 路由函数
│       │   ├── acfun.py
│       │   ├── bilibili.py
│       │   ├── douyin.py
│       │   ├── doupai.py
│       │   ├── haokan.py
│       │   ├── huya.py
│       │   ├── kuaishou.py
│       │   ├── lishipin.py
│       │   ├── lvzhou.py
│       │   ├── meipai.py
│       │   ├── pipigaoxiao.py
│       │   ├── pipixia.py
│       │   ├── quanmin.py
│       │   ├── quanminkge.py
│       │   ├── redbook.py
│       │   ├── sixroom.py
│       │   ├── twitter.py
│       │   ├── weibo.py
│       │   ├── weishi.py
│       │   ├── xigua.py
│       │   ├── xinpianchang.py
│       │   └── zuiyou.py
│       ├── web.py                     # FastAPI 应用（从 main.py 提取）
│       ├── utils.py                   # 工具函数（从 utils/__init__.py 合并）
│       └── cli/                       # CLI 模块
│           ├── __init__.py            # typer app + 根命令（默认 serve）
│           ├── parse.py               # parse 子命令
│           ├── serve.py               # serve 子命令
│           ├── version.py             # version 子命令
│           └── output.py              # 输出格式化（text/json）
├── templates/                         # Web 模板（保持原位）
├── tests/                             # 测试目录
├── main.py                            # 开发入口（薄壳）
├── Dockerfile                         # 更新为 uv 安装方式
└── requirements.txt                   # 保留兼容（标注为遗留）
```

### pyproject.toml 配置

```toml
[project]
name = "parse-video-py"
version = "0.0.2"
description = "视频解析服务，支持 20+ 平台去水印解析"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
    "aiohttp>=3.9",
    "fake-useragent>=1.5",
    "lxml>=5.0",
    "parsel>=1.9",
    "httpx>=0.27",
    "jmespath>=1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
web = [
    "fastapi>=0.110",
    "uvicorn>=0.29",
    "jinja2>=3.1",
    "python-multipart>=0.0.20",
    "fastapi-mcp>=0.4",
]
cli = [
    "typer>=0.12",
    "rich>=13.0",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "black>=24.0",
    "isort>=5.13",
    "flake8>=7.0",
    "pre-commit>=3.7",
]
all = ["parse-video-py[web,cli]"]

[project.scripts]
parse-video-py = "parse_video_py.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/parse_video_py"]

[tool.black]
line-length = 88

[tool.isort]
profile = "black"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 核心依赖拆分

**核心依赖**（解析功能必需）：
- aiohttp, fake-useragent, lxml, parsel, httpx, jmespath, pyyaml

**可选依赖**：
- `web`：fastapi, uvicorn, jinja2, python-multipart, fastapi-mcp
- `cli`：typer, rich
- `dev`：pytest, pytest-asyncio, black, isort, flake8, pre-commit

### 公开 API（`src/parse_video_py/__init__.py`）

```python
from .base import VideoAuthor, VideoInfo, VideoSource
from .parser import parse_video_id, parse_video_share_url

__all__ = [
    "VideoSource",
    "VideoInfo",
    "VideoAuthor",
    "parse_video_share_url",
    "parse_video_id",
]
```

用户使用方式：
```python
from parse_video_py import parse_video_share_url, VideoSource
import asyncio

video_info = asyncio.run(parse_video_share_url("https://v.douyin.com/xxx"))
```

### CLI 命令设计（对齐 Go 版）

```bash
# 解析命令
parse-video-py parse "https://v.douyin.com/xxx"
parse-video-py parse "https://v.douyin.com/xxx" --format json
parse-video-py parse "https://v.douyin.com/xxx" -d -o ./downloads
parse-video-py parse -f urls.txt
parse-video-py parse -f -

# 启动服务
parse-video-py serve --port 8000 --host 0.0.0.0

# 版本信息
parse-video-py version
```

#### CLI 模块结构

**`src/parse_video_py/cli/__init__.py`**：
- 创建 typer app 实例
- 不带子命令时显示帮助信息

**`src/parse_video_py/cli/parse.py`**：
- 接受多个 URL 参数
- `--format json|text` 输出格式
- `--download / -d` 下载媒体
- `--output-dir / -o` 下载目录
- `--file / -f` 从文件/stdin 读取 URL
- 支持单条和批量解析（批量使用 asyncio.gather 并发）

**`src/parse_video_py/cli/serve.py`**：
- `--host` 监听地址
- `--port` 监听端口
- 通过 uvicorn 启动 FastAPI 应用

**`src/parse_video_py/cli/version.py`**：
- 输出 `parse-video-py <version>`

**`src/parse_video_py/cli/output.py`**：
- text 格式输出（对齐 Go 版 formatTextOutput）
- json 格式输出（美化缩进）

### Web 服务（`src/parse_video_py/web.py`）

从现有 `main.py` 提取，关键改动：

1. **模板路径处理**：`templates/` 保留在项目根目录。Web 服务通过 `pathlib.Path` 定位模板目录，支持两种场景：
   - 开发模式：相对于项目根目录的 `templates/`
   - 包安装模式：相对于 `web.py` 模块位置向上查找 `templates/`
2. 提供 `create_app()` 工厂函数
3. 模块级 `app = create_app()` 供 uvicorn 使用

```python
from pathlib import Path

def _get_templates_dir() -> str:
    """定位模板目录，兼容开发模式和包安装模式"""
    # 优先查找项目根目录的 templates/
    project_root = Path(__file__).parent.parent.parent
    templates_dir = project_root / "templates"
    if templates_dir.is_dir():
        return str(templates_dir)
    # 回退到包内查找
    raise FileNotFoundError("templates 目录未找到")

def create_app() -> FastAPI:
    templates_dir = _get_templates_dir()
    app = FastAPI()
    # ... 原有路由和中间件配置
    return app

app = create_app()
```

### 开发入口（`main.py`）

```python
import uvicorn
from parse_video_py.web import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Dockerfile 更新

```dockerfile
FROM python:3.10-slim

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 复制项目文件
COPY . .

# 使用 uv 安装依赖（包含所有可选依赖）
RUN uv pip install --system ".[all]"

EXPOSE 8000

CMD ["uvicorn", "parse_video_py.web:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 测试更新

- 所有 import 路径从 `from parser import ...` 改为 `from parse_video_py.parser import ...`
- 测试配置更新 `conftest.py` 中的路径
- 新增 CLI 测试（typer.testing.TestClient）

### 安装方式

```bash
# 仅核心解析功能
uv pip install -e .

# 全部功能
uv pip install -e ".[all]"

# 仅 Web 服务
uv pip install -e ".[web]"

# 仅 CLI
uv pip install -e ".[cli]"

# 从 git 安装
uv pip install git+https://github.com/wujunwei928/parse-video-py.git
```

## 改造影响范围

### 需要改动的文件

1. **新增**：`pyproject.toml`、`src/parse_video_py/__init__.py`、`src/parse_video_py/web.py`、`src/parse_video_py/cli/*.py`
2. **移动**：`parser/` → `src/parse_video_py/parser/`、`utils/__init__.py` → `src/parse_video_py/utils.py`
3. **修改**：所有 parser 文件的 import 路径、测试文件、Dockerfile
   - parser 内部：`from utils import ...` → `from parse_video_py.utils import ...`
   - parser 内部：`from .base import ...` 保持不变（相对导入）
   - 测试文件：`from parser import ...` → `from parse_video_py import ...`
   - `main.py`：`from parser import ...` → `from parse_video_py import ...`
4. **保留**：`templates/`、`resources/`、`main.py`（薄入口）

### 不破坏的兼容性

- API 路由路径不变：`/video/share/url/parse`、`/video/id/parse`
- Basic Auth 环境变量不变：`PARSE_VIDEO_USERNAME`、`PARSE_VIDEO_PASSWORD`
- MCP 端点不变

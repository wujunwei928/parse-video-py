# uv 包管理 + src 布局改造 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 parse-video-py 从 venv+requirements.txt 迁移到 uv 包管理，采用 src 标准布局，支持 Python API / CLI / Web 服务三种使用方式。

**Architecture:** 将现有 `parser/` 移入 `src/parse_video_py/parser/`，`utils/` 合并为 `src/parse_video_py/utils.py`，`templates/` 移入 `src/parse_video_py/templates/`（确保打包进 wheel），新增 CLI 模块（typer），从 `main.py` 提取 Web 服务到 `src/parse_video_py/web.py`。通过 `pyproject.toml` 定义包元数据和入口点。

**Tech Stack:** Python 3.10+, uv, hatchling, FastAPI, typer, httpx, httpx

---

## 文件变更总览

| 操作 | 源路径 | 目标路径 |
|------|--------|----------|
| 新建 | - | `pyproject.toml` |
| 新建 | - | `src/parse_video_py/__init__.py` |
| 新建 | - | `src/parse_video_py/utils.py` |
| 新建 | - | `src/parse_video_py/web.py` |
| 新建 | - | `src/parse_video_py/cli/__init__.py` |
| 新建 | - | `src/parse_video_py/cli/_parse.py` |
| 新建 | - | `src/parse_video_py/cli/output.py` |
| 新建 | - | `src/parse_video_py/cli/output.py` |
| 移动 | `parser/*.py`（含 base.py 和所有解析器） | `src/parse_video_py/parser/*.py` |
| 移动 | `parser/__init__.py` | `src/parse_video_py/parser/__init__.py` |
| 移动 | `templates/` | `src/parse_video_py/templates/`（打包进 wheel） |
| 改写 | `main.py` | `main.py`（薄入口） |
| 更新 | `Dockerfile` | `Dockerfile` |
| 更新 | `tests/test_main.py` | `tests/test_main.py` |
| 更新 | `tests/test_twitter.py` | `tests/test_twitter.py` |
| 新建 | - | `tests/test_cli.py` |
| 删除 | `utils/__init__.py` | -（内容合入 `src/parse_video_py/utils.py`） |
| 删除 | `parser/`（整个旧目录） | - |
| 更新 | `.github/workflows/python-app.yml` | 改用 uv 安装 |

---

### Task 1: 创建 pyproject.toml 和 uv 虚拟环境

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: 创建 pyproject.toml**

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
    "pytest-timeout>=2.2",
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

- [ ] **Step 2: 删除旧 .venv 目录**

```bash
rm -rf /code/parse-video-py/.venv
```

- [ ] **Step 3: 用 uv 创建虚拟环境并安装全部依赖**

```bash
cd /code/parse-video-py && uv venv && uv pip install -e ".[all,dev]"
```

- [ ] **Step 4: 验证虚拟环境创建成功**

```bash
cd /code/parse-video-py && source .venv/bin/activate && python -c "import httpx; print('uv 环境正常')"
```

Expected: 输出 `uv 环境正常`

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml
git commit -m "feat: 添加 pyproject.toml，迁移到 uv 包管理"
```

---

### Task 2: 创建 src 布局目录结构并移动 parser 和 utils

**Files:**
- Move: `parser/*.py`（含 base.py 和所有解析器） → `src/parse_video_py/parser/*.py`
- Move: `parser/__init__.py` → `src/parse_video_py/parser/__init__.py`
- Create: `src/parse_video_py/utils.py`（从 `utils/__init__.py` 内容）
- Delete: `parser/`（旧目录，移动后删除）
- Delete: `utils/`（旧目录，移动后删除）

> **注意：** `base.py` 必须保留在 `src/parse_video_py/parser/base.py`，因为 `parser/__init__.py` 和各解析器通过 `from .base import ...` 相对导入。顶层包通过 `__init__.py` 的 `from .parser.base import ...` 来 re-export 公开类型。

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p /code/parse-video-py/src/parse_video_py/parser
mkdir -p /code/parse-video-py/src/parse_video_py/cli
```

- [ ] **Step 2: 复制所有文件（含 base.py）到新位置**

```bash
cp /code/parse-video-py/parser/*.py /code/parse-video-py/src/parse_video_py/parser/
```

这会将 `base.py`、`__init__.py` 以及所有 22 个解析器文件一并复制到 `src/parse_video_py/parser/` 中，保持 `from .base import ...` 相对导入不变。

- [ ] **Step 2b: 移动 templates 到包内**

```bash
mv /code/parse-video-py/templates /code/parse-video-py/src/parse_video_py/templates
```

> 将 `templates/` 移入 `src/parse_video_py/templates/`，确保打包进 wheel 后非 editable 安装也能正常加载模板。

- [ ] **Step 4: 创建 utils.py（将 utils/__init__.py 的内容复制过来）**

创建 `src/parse_video_py/utils.py`：

```python
from urllib.parse import parse_qs, urlparse


def get_val_from_url_by_query_key(url: str, query_key: str) -> str:
    """
    从url的query参数中解析出query_key对应的值
    :param url: url地址
    :param query_key: query参数的key
    :return:
    """
    url_res = urlparse(url)
    url_query = parse_qs(url_res.query, keep_blank_values=True)

    try:
        query_val = url_query[query_key][0]
    except KeyError:
        raise KeyError(f"url中不存在query参数: {query_key}")

    if len(query_val) == 0:
        raise ValueError(f"url中query参数值长度为0: {query_key}")

    return url_query[query_key][0]
```

- [ ] **Step 5: 更新 parser 内部所有 `from utils import` 为 `from parse_video_py.utils import`**

需要修改以下 8 个文件中的 import 行：

- `src/parse_video_py/parser/quanminkge.py:7` — `from utils import` → `from parse_video_py.utils import`
- `src/parse_video_py/parser/weibo.py:7` — `from utils import` → `from parse_video_py.utils import`
- `src/parse_video_py/parser/quanmin.py:3` — `from utils import` → `from parse_video_py.utils import`
- `src/parse_video_py/parser/haokan.py:3` — `from utils import` → `from parse_video_py.utils import`
- `src/parse_video_py/parser/weishi.py:3` — `from utils import` → `from parse_video_py.utils import`
- `src/parse_video_py/parser/zuiyou.py:3` — `from utils import` → `from parse_video_py.utils import`
- `src/parse_video_py/parser/sixroom.py:4` — `from utils import` → `from parse_video_py.utils import`
- `src/parse_video_py/parser/doupai.py:3` — `from utils import` → `from parse_video_py.utils import`

每个文件的具体修改（以 quanminkge.py 为例，其余同理替换 `from utils import` 为 `from parse_video_py.utils import`）：

`src/parse_video_py/parser/quanminkge.py` 第 7 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

`src/parse_video_py/parser/weibo.py` 第 7 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

`src/parse_video_py/parser/quanmin.py` 第 3 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

`src/parse_video_py/parser/haokan.py` 第 3 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

`src/parse_video_py/parser/weishi.py` 第 3 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

`src/parse_video_py/parser/zuiyou.py` 第 3 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

`src/parse_video_py/parser/sixroom.py` 第 4 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

`src/parse_video_py/parser/doupai.py` 第 3 行：
```python
# 旧
from utils import get_val_from_url_by_query_key
# 新
from parse_video_py.utils import get_val_from_url_by_query_key
```

- [ ] **Step 6: 删除旧的 parser/ 和 utils/ 目录**

```bash
rm -rf /code/parse-video-py/parser
rm -rf /code/parse-video-py/utils
rm -rf /code/parse-video-py/__pycache__
```

- [ ] **Step 7: 验证 import 可用**

```bash
cd /code/parse-video-py && source .venv/bin/activate && python -c "from parse_video_py.parser import parse_video_share_url; print('parser import 正常')"
```

Expected: 输出 `parser import 正常`

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "refactor: 将 parser 和 utils 迁移到 src/parse_video_py 布局"
```

---

### Task 3: 创建包公开 API 入口（__init__.py）

**Files:**
- Create: `src/parse_video_py/__init__.py`

- [ ] **Step 1: 创建 __init__.py**

创建 `src/parse_video_py/__init__.py`：

```python
from .parser.base import VideoAuthor, ImgInfo, VideoInfo, VideoSource
from .parser import parse_video_id, parse_video_share_url

__all__ = [
    "VideoSource",
    "VideoInfo",
    "VideoAuthor",
    "ImgInfo",
    "parse_video_share_url",
    "parse_video_id",
]
```

- [ ] **Step 2: 验证公开 API 可用**

```bash
cd /code/parse-video-py && source .venv/bin/activate && python -c "from parse_video_py import VideoSource, parse_video_share_url; print('公开 API 正常')"
```

Expected: 输出 `公开 API 正常`

- [ ] **Step 3: 提交**

```bash
git add src/parse_video_py/__init__.py
git commit -m "feat: 添加包公开 API 入口"
```

---

### Task 4: 提取 Web 服务到 web.py 并改写 main.py

**Files:**
- Create: `src/parse_video_py/web.py`
- Modify: `main.py`（改写为薄入口）

- [ ] **Step 1: 创建 web.py**

创建 `src/parse_video_py/web.py`，内容从 `main.py` 提取，更新 import 路径和模板目录定位：

```python
import os
import re
import secrets
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi_mcp import FastApiMCP

from parse_video_py import VideoSource, parse_video_id, parse_video_share_url


def _get_templates_dir() -> str:
    """定位模板目录（包内 templates/）"""
    # 模板已移入 src/parse_video_py/templates/，与 web.py 同级
    templates_dir = Path(__file__).parent / "templates"
    if templates_dir.is_dir():
        return str(templates_dir)
    raise FileNotFoundError("templates 目录未找到")


app = FastAPI()

mcp = FastApiMCP(app)
mcp.mount_http()

templates = Jinja2Templates(directory=_get_templates_dir())

URL_REG = re.compile(r"http[s]?:\/\/[\w.-]+[\w\/-]*[\w.-]*\??[\w=&:\-\+\%]*[/]*")


def get_auth_dependency() -> list[Depends]:
    """
    根据环境变量动态返回 Basic Auth 依赖项
    """
    basic_auth_username = os.getenv("PARSE_VIDEO_USERNAME")
    basic_auth_password = os.getenv("PARSE_VIDEO_PASSWORD")

    if not (basic_auth_username and basic_auth_password):
        return []

    security = HTTPBasic()

    def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
        correct_username = secrets.compare_digest(
            credentials.username, basic_auth_username
        )
        correct_password = secrets.compare_digest(
            credentials.password, basic_auth_password
        )
        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials

    return [Depends(verify_credentials)]


@app.get("/", response_class=HTMLResponse, dependencies=get_auth_dependency())
async def read_item(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "github.com/wujunwei928/parse-video-py Demo",
        },
    )


@app.get("/video/share/url/parse", dependencies=get_auth_dependency())
async def share_url_parse(url: str):
    matched_url = URL_REG.search(url)
    if matched_url is None:
        return {
            "code": 400,
            "msg": "未检测到有效的分享链接",
        }

    video_share_url = matched_url.group()

    try:
        video_info = await parse_video_share_url(video_share_url)
        return {"code": 200, "msg": "解析成功", "data": video_info.__dict__}
    except Exception as err:
        return {
            "code": 500,
            "msg": str(err),
        }


@app.get("/video/id/parse", dependencies=get_auth_dependency())
async def video_id_parse(source: VideoSource, video_id: str):
    try:
        video_info = await parse_video_id(source, video_id)
        return {"code": 200, "msg": "解析成功", "data": video_info.__dict__}
    except Exception as err:
        return {
            "code": 500,
            "msg": str(err),
        }


mcp.setup_server()
```

- [ ] **Step 2: 改写 main.py 为薄入口**

改写 `main.py` 全文：

```python
import uvicorn

from parse_video_py.web import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 3: 验证 Web 应用可启动**

```bash
cd /code/parse-video-py && source .venv/bin/activate && python -c "from parse_video_py.web import app; print('Web 应用加载正常')"
```

Expected: 输出 `Web 应用加载正常`

- [ ] **Step 4: 提交**

```bash
git add src/parse_video_py/web.py main.py
git commit -m "feat: 提取 Web 服务到 web.py，main.py 改为薄入口"
```

---

### Task 5: 实现 CLI output 模块

**Files:**
- Create: `src/parse_video_py/cli/output.py`

- [ ] **Step 1: 创建 output.py**

创建 `src/parse_video_py/cli/output.py`，对齐 Go 版 `cmd/output.go` 的输出格式：

```python
"""CLI 输出格式化模块，对齐 Go 版 parse-video 的输出格式"""

import dataclasses
import json
import sys

from parse_video_py.parser.base import VideoInfo


def format_text_output(info: VideoInfo) -> str:
    """文本格式输出（对齐 Go 版 formatTextOutput）"""
    lines = []
    lines.append(f"标题: {info.title}")
    lines.append(f"作者: {info.author.name} (UID: {info.author.uid})")
    if info.video_url:
        lines.append(f"视频地址: {info.video_url}")
    if info.cover_url:
        lines.append(f"封面地址: {info.cover_url}")
    if info.music_url:
        lines.append(f"音乐地址: {info.music_url}")
    if info.images:
        lines.append("图片列表:")
        for i, img in enumerate(info.images, 1):
            if img.live_photo_url:
                lines.append(f"  [{i}] {img.url} (LivePhoto: {img.live_photo_url})")
            else:
                lines.append(f"  [{i}] {img.url}")
    else:
        lines.append("图片数量: 0")
    return "\n".join(lines)


def format_json_output(info: VideoInfo) -> str:
    """JSON 格式输出"""
    data = dataclasses.asdict(info)
    return json.dumps(data, ensure_ascii=False, indent=2)


def output_result(info: VideoInfo, fmt: str = "text") -> None:
    """输出单条解析结果到 stdout"""
    if fmt == "json":
        print(format_json_output(info))
    else:
        print(format_text_output(info))


def output_batch_error(input_url: str, error_msg: str) -> None:
    """输出批量解析中的错误"""
    print(f"[失败] {input_url}", file=sys.stderr)
    print(f"错误: {error_msg}", file=sys.stderr)
```

- [ ] **Step 2: 提交**

```bash
git add src/parse_video_py/cli/output.py
git commit -m "feat: 添加 CLI 输出格式化模块"
```

---

### Task 6: 实现 CLI 入口（__init__.py）— 包含 version、serve、parse 注册

**Files:**
- Create: `src/parse_video_py/cli/__init__.py`

- [ ] **Step 1: 创建 cli/__init__.py**

所有子命令直接注册在主 typer app 上。serve 中的 uvicorn 和 parse 中的解析逻辑均使用延迟导入，确保只安装 `.[cli]` 时 `parse-video-py version` 和 `parse-video-py parse` 也能正常工作。

创建 `src/parse_video_py/cli/__init__.py`：

```python
"""parse-video-py CLI 工具"""

import typer

app = typer.Typer(
    name="parse-video-py",
    help="视频解析工具，支持 20+ 平台去水印解析",
    add_completion=False,
)


@app.command()
def version():
    """显示版本信息"""
    typer.echo("parse-video-py 0.0.2")


@app.command()
def parse(
    urls: list[str] = typer.Argument(None, help="视频分享链接"),
    format: str = typer.Option("text", "--format", help="输出格式: json, text"),
    file: str = typer.Option(None, "--file", "-f", help="从文件读取链接（每行一个，- 代表 stdin）"),
):
    """解析视频分享链接，支持单条和多条"""
    # 延迟导入，避免循环依赖
    from parse_video_py.cli._parse import run_parse

    run_parse(urls, format, file)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="服务监听地址"),
    port: int = typer.Option(8000, "--port", "-p", help="服务监听端口"),
):
    """启动 HTTP 解析服务"""
    # 延迟导入 uvicorn，避免只安装 .[cli] 时因缺少 uvicorn 导致整个 CLI 崩溃
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "错误: uvicorn 未安装。请使用 parse-video-py[web] 安装 Web 服务依赖",
            err=True,
        )
        raise typer.Exit(code=1)
    uvicorn.run(
        "parse_video_py.web:app",
        host=host,
        port=port,
        reload=False,
    )
```

- [ ] **Step 2: 验证 CLI 入口可加载**

```bash
cd /code/parse-video-py && source .venv/bin/activate && python -c "from parse_video_py.cli import app; print('CLI 入口加载正常')"
```

Expected: 输出 `CLI 入口加载正常`

- [ ] **Step 3: 提交**

```bash
git add src/parse_video_py/cli/__init__.py
git commit -m "feat: 添加 CLI 入口，注册 version/parse/serve 子命令"
```

---

### Task 7: 实现 CLI parse 逻辑模块（_parse.py）

**Files:**
- Create: `src/parse_video_py/cli/_parse.py`

- [ ] **Step 1: 创建 _parse.py**

创建 `src/parse_video_py/cli/_parse.py`，包含 parse 命令的核心逻辑，对齐 Go 版 `cmd/parse.go` 的功能：

```python
"""CLI parse 命令核心逻辑"""

import asyncio
import re
import sys
from pathlib import Path
from typing import List, Optional

import typer

from parse_video_py import parse_video_share_url
from parse_video_py.parser.base import VideoInfo
from parse_video_py.cli.output import format_json_output, format_text_output

URL_REG = re.compile(r"http[s]?:\/\/[\w.-]+[\w\/-]*[\w.-]*\??[\w=&:\-\+\%]*[/]*")


def _extract_url(text: str) -> Optional[str]:
    """从文本中提取 URL"""
    match = URL_REG.search(text)
    return match.group() if match else None


def _read_inputs_from_file(file_path: str) -> List[str]:
    """从文件读取 URL 列表，每行一个"""
    if file_path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        p = Path(file_path)
        if not p.exists():
            typer.echo(f"无法读取文件: {file_path}", err=True)
            raise typer.Exit(code=1)
        lines = p.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


async def _parse_single(url: str) -> tuple[Optional[VideoInfo], Optional[str]]:
    """解析单条 URL，返回 (VideoInfo, error_msg)"""
    try:
        extracted = _extract_url(url)
        if not extracted:
            return None, f"未检测到有效的分享链接: {url}"
        info = await parse_video_share_url(extracted)
        return info, None
    except Exception as e:
        return None, str(e)


async def _parse_batch(urls: List[str]) -> List[tuple[str, Optional[VideoInfo], Optional[str]]]:
    """批量解析 URL"""
    tasks = [_parse_single(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return [(url, info, err) for url, (info, err) in zip(urls, results)]


def run_parse(urls: Optional[list[str]], format: str, file: Optional[str]) -> None:
    """parse 命令入口，由 cli/__init__.py 延迟调用"""
    # 验证 format 参数
    if format not in ("json", "text"):
        typer.echo(f"不支持的输出格式: {format}，可选值: json, text", err=True)
        raise typer.Exit(code=1)

    # 检查参数冲突
    if urls and file:
        typer.echo("不能同时指定链接和文件输入", err=True)
        raise typer.Exit(code=1)

    # 获取输入列表
    inputs: List[str] = []
    if file:
        inputs = _read_inputs_from_file(file)
    elif urls:
        inputs = list(urls)
    else:
        typer.echo("请提供要解析的链接或指定 --file", err=True)
        raise typer.Exit(code=1)

    if not inputs:
        return

    # 解析
    if len(inputs) == 1:
        info, err = asyncio.run(_parse_single(inputs[0]))
        if err:
            typer.echo(f"解析失败: {err}", err=True)
            raise typer.Exit(code=1)
        if format == "json":
            print(format_json_output(info))
        else:
            print(format_text_output(info))
    else:
        results = asyncio.run(_parse_batch(inputs))
        fail_count = 0
        for i, (url, info, err) in enumerate(results):
            if i > 0 and format == "text":
                print()
            if err:
                print(f"[失败] {url}", file=sys.stderr)
                print(f"错误: {err}", file=sys.stderr)
                fail_count += 1
            else:
                if format == "json":
                    print(format_json_output(info))
                else:
                    print(format_text_output(info))
        if fail_count == len(inputs):
            typer.echo(f"所有 {len(inputs)} 条解析均失败", err=True)
            raise typer.Exit(code=1)
```

- [ ] **Step 2: 提交**

```bash
git add src/parse_video_py/cli/_parse.py
git commit -m "feat: 添加 CLI parse 核心逻辑，支持单条/批量解析"
```

---

### Task 8: 更新测试文件

**Files:**
- Modify: `tests/test_main.py`
- Modify: `tests/test_twitter.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: 更新 test_main.py**

改写 `tests/test_main.py` 全文，更新 import 路径：

```python
from fastapi.testclient import TestClient

from parse_video_py.web import app

client = TestClient(app)


def test_share_url_parse_returns_400_when_no_url_found():
    response = client.get("/video/share/url/parse", params={"url": "这不是链接"})

    assert response.status_code == 200
    assert response.json() == {"code": 400, "msg": "未检测到有效的分享链接"}


def test_share_url_parse_returns_400_for_empty_string():
    response = client.get("/video/share/url/parse", params={"url": ""})

    assert response.status_code == 200
    assert response.json() == {"code": 400, "msg": "未检测到有效的分享链接"}


def test_share_url_parse_returns_400_for_partial_url_without_scheme():
    response = client.get(
        "/video/share/url/parse", params={"url": "example.com/video/123"}
    )

    assert response.status_code == 200
    assert response.json() == {"code": 400, "msg": "未检测到有效的分享链接"}


def test_share_url_parse_returns_422_when_url_param_missing():
    response = client.get("/video/share/url/parse")

    assert response.status_code == 422
```

- [ ] **Step 2: 更新 test_twitter.py**

改写 `tests/test_twitter.py` 全文，更新 import 路径：

```python
import pytest

from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.twitter import Twitter


class TestTwitterToken:
    """测试 token 计算逻辑"""

    def test_get_token_normal_id(self):
        """测试普通推文 ID 的 token 生成"""
        tw = Twitter()
        token = tw._get_token("1849000000000000000")
        assert len(token) > 0

    def test_get_token_short_id(self):
        """测试短 ID 的 token 生成"""
        tw = Twitter()
        token = tw._get_token("123456789")
        assert len(token) > 0

    def test_get_token_long_id(self):
        """测试长 ID 的 token 生成"""
        tw = Twitter()
        token = tw._get_token("1879553847283155177")
        assert len(token) > 0


class TestTwitterExtractTweetId:
    """测试推文 ID 提取"""

    def test_x_com_standard_url(self):
        """测试 x.com 标准链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://x.com/elonmusk/status/1849000000000000000"
        )
        assert tweet_id == "1849000000000000000"

    def test_twitter_com_standard_url(self):
        """测试 twitter.com 标准链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://twitter.com/elonmusk/status/1849000000000000000"
        )
        assert tweet_id == "1849000000000000000"

    def test_url_with_query_params(self):
        """测试带查询参数的链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://x.com/user/status/1849000000000000000?s=20"
        )
        assert tweet_id == "1849000000000000000"

    def test_mobile_twitter_com(self):
        """测试 mobile.twitter.com 链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://mobile.twitter.com/user/status/1849000000000000000"
        )
        assert tweet_id == "1849000000000000000"

    def test_invalid_url(self):
        """测试无效链接"""
        tw = Twitter()
        with pytest.raises(ValueError):
            tw._extract_tweet_id("https://x.com/user/likes")

    def test_empty_string(self):
        """测试空字符串"""
        tw = Twitter()
        with pytest.raises(ValueError):
            tw._extract_tweet_id("")


class TestTwitterVideoSource:
    """测试 VideoSource 枚举值"""

    def test_twitter_video_source_exists(self):
        """测试 Twitter VideoSource 枚举存在"""
        assert VideoSource.Twitter.value == "twitter"
```

- [ ] **Step 3: 创建 test_cli.py**

创建 `tests/test_cli.py`：

```python
"""CLI 模块单元测试"""

from typer.testing import CliRunner

from parse_video_py.cli import app

runner = CliRunner()


class TestVersionCommand:
    """测试 version 子命令"""

    def test_version_output(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "parse-video-py" in result.output
        assert "0.0.2" in result.output


class TestParseCommand:
    """测试 parse 子命令"""

    def test_parse_no_args_shows_error(self):
        result = runner.invoke(app, ["parse"])
        assert result.exit_code != 0

    def test_parse_invalid_format(self):
        result = runner.invoke(
            app, ["parse", "https://example.com", "--format", "xml"]
        )
        assert result.exit_code != 0
        assert "不支持的输出格式" in result.output or "xml" in result.output


class TestHelpOutput:
    """测试帮助信息"""

    def test_main_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "parse-video-py" in result.output or "视频解析" in result.output

    def test_parse_help(self):
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0

    def test_serve_help(self):
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
```

- [ ] **Step 4: 运行全部测试**

```bash
cd /code/parse-video-py && source .venv/bin/activate && pytest tests/ -v --timeout=60
```

Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add tests/test_main.py tests/test_twitter.py tests/test_cli.py
git commit -m "test: 更新测试文件 import 路径，添加 CLI 测试"
```

---

### Task 9: 更新 Dockerfile

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: 更新 Dockerfile**

改写 `Dockerfile` 全文：

```dockerfile
FROM python:3.10-slim

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 设置工作目录
WORKDIR /app

# 复制项目文件（templates 已在 src/parse_video_py/templates/ 中）
COPY pyproject.toml .
COPY src/ src/

# 使用 uv 安装依赖（包含所有可选依赖）
RUN uv pip install --system ".[all]"

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 应用
CMD ["uvicorn", "parse_video_py.web:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 验证 Dockerfile 语法**

```bash
cd /code/parse-video-py && docker build --check . 2>&1 || echo "Docker 不可用，跳过构建验证"
```

- [ ] **Step 3: 提交**

```bash
git add Dockerfile
git commit -m "feat: 更新 Dockerfile 使用 uv 安装依赖"
```

---

### Task 10: 更新 CI 配置和清理遗留文件

**Files:**
- Modify: `.github/workflows/python-app.yml`
- Modify: `.gitignore`（添加 uv 相关忽略项）

- [ ] **Step 1: 更新 .github/workflows/python-app.yml**

改写全文：

```yaml
name: Python application

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v4
    - name: Set up Python
      run: uv python install 3.10
    - name: Create venv and install dependencies
      run: |
        uv venv
        uv pip install -e ".[all,dev]"
    - name: Test with pytest
      run: |
        source .venv/bin/activate
        pytest tests/ -v --tb=short
```

- [ ] **Step 2: 更新 .gitignore，添加 uv 相关忽略项**

在 `.gitignore` 末尾添加：

```
# uv
uv.lock
```

- [ ] **Step 3: 清理旧的 requirements.txt（保留但标注遗留）**

在 `requirements.txt` 头部添加注释：

```
# 注意：此文件为遗留文件，依赖管理已迁移到 pyproject.toml
# 新安装请使用：uv pip install -e ".[all]"
```

- [ ] **Step 4: 提交**

```bash
git add .github/workflows/python-app.yml .gitignore requirements.txt
git commit -m "chore: 更新 CI 使用 uv，清理遗留配置"
```

---

### Task 10b: 更新 README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README.md 中"本地运行"部分**

将 README.md 中 `# 运行` 到 `uvicorn main:app --reload` 部分替换为新内容。具体操作：

1. 删除 README.md 中 `### 创建并激活 python 虚拟环境` 整个代码块（第 82-96 行）
2. 删除 `### 安装依赖库` 代码块（第 98-101 行）
3. 将 `### 运行app` 的 `uvicorn main:app --reload` 改为 `uvicorn parse_video_py.web:app --reload`
4. 在 `## 本地运行` 和 `### 如需开启basic auth认证` 之间插入以下新段落（使用文本编辑器写入，不要使用 markdown 代码块包裹）：

写入 README.md 的纯文本内容（从 `### 使用 uv（推荐）` 开始，到 `parse-video-py version` 结束）：

--- 以下为写入 README 的实际内容（非代码块） ---

### 使用 uv（推荐）

    # 进入项目根目录
    cd parse-video-py

    # 创建虚拟环境并安装全部依赖
    uv venv && uv pip install -e ".[all]"

    # 激活虚拟环境
    source .venv/bin/activate

    # 启动 Web 服务
    uvicorn parse_video_py.web:app --reload

### CLI 命令行

    # 安装
    uv pip install -e ".[all]"

    # 解析视频
    parse-video-py parse "https://v.douyin.com/xxx"
    parse-video-py parse "https://v.douyin.com/xxx" --format json

    # 启动 Web 服务
    parse-video-py serve --port 8000

    # 查看版本
    parse-video-py version

--- 以上为写入 README 的实际内容 ---

> 注意：上面的缩进内容使用 4 空格缩进格式（非 ``` 代码块），避免 markdown 嵌套问题。

- [ ] **Step 2: 更新 README.md 中"自己写方法调用"部分**

将 `from parser import parse_video_share_url, parse_video_id, VideoSource` 替换为：

    from parse_video_py import parse_video_share_url, parse_video_id, VideoSource

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: 更新 README 使用 uv 和新的 import 路径"
```

---

### Task 11: 端到端验证

**Files:** 无新文件

- [ ] **Step 1: 重新安装包**

```bash
cd /code/parse-video-py && source .venv/bin/activate && uv pip install -e ".[all,dev]"
```

- [ ] **Step 2: 运行全部测试**

```bash
cd /code/parse-video-py && source .venv/bin/activate && pytest tests/ -v --timeout=60
```

Expected: 所有测试 PASS

- [ ] **Step 3: 验证 CLI 命令可用**

```bash
cd /code/parse-video-py && source .venv/bin/activate && parse-video-py version
```

Expected: 输出 `parse-video-py 0.0.2`

```bash
parse-video-py --help
```

Expected: 显示帮助信息，包含 parse、serve、version 子命令

```bash
parse-video-py parse --help
```

Expected: 显示 parse 命令帮助

```bash
parse-video-py serve --help
```

Expected: 显示 serve 命令帮助

- [ ] **Step 4: 验证 Python API 可用**

```bash
cd /code/parse-video-py && source .venv/bin/activate && python -c "
from parse_video_py import VideoSource, parse_video_share_url, parse_video_id
print('VideoSource 枚举:', VideoSource.DouYin.value)
print('Python API 正常')
"
```

Expected: 输出 `VideoSource 枚举: douyin` 和 `Python API 正常`

- [ ] **Step 5: 验证 Web 服务可启动**

```bash
cd /code/parse-video-py && source .venv/bin/activate && timeout 3 python -c "import uvicorn; from parse_video_py.web import app; uvicorn.run(app, host='127.0.0.1', port=18765)" 2>&1 || true
```

Expected: 看到 `Uvicorn running on http://127.0.0.1:18765` 类似的启动日志

- [ ] **Step 6: 最终提交**

```bash
git add -A
git commit -m "chore: 端到端验证通过，uv 包管理改造完成"
```

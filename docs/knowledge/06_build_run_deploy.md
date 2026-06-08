---
knowledge_version: 1
last_scanned_at: 2026-06-08
source_commit: dd55df3
---

# 构建运行部署

## 本地开发环境

| 依赖 | 版本/要求 | 证据来源 |
|---|---|---|
| Python | >=3.10 | `pyproject.toml:requires-python` |
| uv | 最新版（包管理+虚拟环境） | `README.md:69-78` |
| hatchling | 构建后端 | `pyproject.toml:build-backend` |

## 环境变量

| 变量 | 用途 | 是否敏感 | 默认值/示例 | 使用位置 | 证据来源 |
|---|---|---|---|---|---|
| `PARSE_VIDEO_USERNAME` | Basic Auth 用户名 | 是 | 不设置=不开启 | `web.py:34` | `web.py:34` |
| `PARSE_VIDEO_PASSWORD` | Basic Auth 密码 | 是 | 不设置=不开启 | `web.py:35` | `web.py:35` |

## 安装依赖

```bash
# 创建虚拟环境并安装全部依赖（推荐）
uv venv && uv pip install -e ".[all]"

# 仅安装核心+Web
uv pip install -e ".[web]"

# 仅安装核心+CLI
uv pip install -e ".[cli]"

# 安装开发依赖
uv pip install -e ".[all,dev]"
```

## 本地启动

```bash
# 开发模式（自动重载）
uvicorn main:app --reload

# 生产模式
uvicorn parse_video_py.web:app --host 0.0.0.0 --port 8000

# CLI 启动 Web 服务
parse-video-py serve --port 8000
```

## 测试命令

```bash
# 运行全部测试
pytest tests/ -v --tb=short

# 运行单个测试文件
pytest tests/test_utils.py -v

# 带超时限制（防止卡死）
pytest tests/ -v --tb=short --timeout=60

# 带覆盖率
pytest --cov=parse_video_py
```

## 代码质量检查

```bash
# 格式化
black .
isort .

# Lint
flake8 .

# 全部 pre-commit 检查
pre-commit run --all-files
```

## 构建命令

```bash
# 构建 wheel 包
uv build

# Docker 构建
docker build -t parse-video-py .
```

## 部署方式

**Docker 部署**（主要方式）：

- Dockerfile：`python:3.10-slim` + uv 安装依赖
- 暴露端口：8000
- 启动命令：`uvicorn parse_video_py.web:app --host 0.0.0.0 --port 8000`
- CI/CD：GitHub Actions 自动构建推送到 Docker Hub（`docker.yml`）
- 镜像：`wujunwei928/parse-video-py:latest`
- 证据来源：`Dockerfile`、`.github/workflows/docker.yml`

**CI/CD 流程**：

- `python-app.yml`：push/PR 到 main → 安装依赖 → 运行 pytest
- `docker.yml`：push 到 main → 构建 Docker 镜像 → 推送 Docker Hub

## 数据库初始化/迁移

当前项目无数据库，不需要初始化或迁移。

## 常见问题

| 问题 | 可能原因 | 排查方式 | 相关文件 |
|---|---|---|---|
| 解析失败返回 500 | 平台接口变更、分享链接过期 | 检查对应解析器的 HTTP 请求和响应 | `parser/<平台>.py` |
| "未检测到有效的分享链接" | URL 格式不匹配正则 | 检查 `utils.py:URL_REG` 正则 | `utils.py:4` |
| "does not have source config" | URL 域名未在映射表中 | 检查 `video_source_info_mapping` 的 `domain_list` | `parser/__init__.py:29-145` |
| Docker 构建失败 | 依赖安装问题 | 检查 `pyproject.toml` 和网络 | `Dockerfile` |
| pre-commit pytest 卡死 | 测试超时 | 添加 `--timeout=60` | `.pre-commit-config.yaml` |

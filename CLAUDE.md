# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based video parsing service that extracts video information from multiple Chinese social media platforms. It removes watermarks and provides direct video URLs from 20+ platforms including Douyin, Kuaishou, Weibo, Xiaohongshu, and others.

## Architecture

Source code lives under `src/parse_video_py/` (hatchling build).

- **Web** (`src/parse_video_py/web.py`): FastAPI app, routes, global Basic Auth middleware, MCP
- **Parsers** (`src/parse_video_py/parser/`): 25 platform parsers inheriting `BaseParser`
- **Outbound boundary** (`src/parse_video_py/outbound.py`): per-platform domain allowlist, public-IP and URL shape checks, sensitive-header stripping, response size limit (`CheckedAsyncTransport`); see `docs/adr/0002`
- **CLI** (`src/parse_video_py/cli/`): Typer commands (parse/serve/version)
- **Utils** (`src/parse_video_py/utils.py`): URL extraction, query param parsing, HTTP client factory with proxy/timeout defaults

### Core Components

**BaseParser** (`src/parse_video_py/parser/base.py`):
- Abstract base class for all platform parsers
- Defines `VideoSource` enum (25 platforms), `VideoInfo`, `VideoAuthor`, `ImgInfo` dataclasses
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
- 25 platforms support video, 5 also support image albums (Douyin, Kuaishou, Xiaohongshu, Pipixia, Weibo)
- LivePhoto support: Douyin and Xiaohongshu
- Image parsers should prioritize highest quality: large > original > bmiddle > url
- Use app share links when possible; desktop web versions may not be fully tested
- Auth uses `secrets.compare_digest()` — do not replace with plain string comparison

## Adding New Platforms

1. Create `src/parse_video_py/parser/<name>.py` inheriting from `BaseParser`
2. Add enum value to `VideoSource` in `base.py`
3. Update `video_source_info_mapping` in `parser/__init__.py` with domain list and parser class
4. Add any platform API/short-link/redirect hosts beyond the share domains to `UPSTREAM_DOMAINS` in `outbound.py` (otherwise outbound requests get rejected)
5. Create HTTP clients via `create_async_client(source=VideoSource.<Name>, ...)` so requests go through the outbound boundary
6. Implement `parse_share_url()` and `parse_video_id()`
7. Add tests in `tests/test_<name>.py`

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

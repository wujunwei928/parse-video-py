# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based video parsing service that extracts video information from multiple Chinese social media platforms. It removes watermarks and provides direct video URLs from 20+ platforms including Douyin, Kuaishou, Weibo, Xiaohongshu, and others.

## Architecture

The application follows a modular architecture:

- **FastAPI Web Framework** (`main.py`): Provides REST API endpoints and web interface
- **Parser Module** (`parser/`): Contains platform-specific parsers with a common base class
- **Template System** (`templates/`): Jinja2 templates for the web interface
- **Utilities** (`utils/`): Shared utility functions

### Core Components

**BaseParser System** (`parser/base.py`):
- Abstract base class defining the interface for all platform parsers
- Provides common headers using fake-useragent
- Defines data structures: `VideoInfo`, `VideoAuthor`, `ImgInfo`

**Platform Parsers** (`parser/`):
Each platform has its own parser inheriting from `BaseParser`:
- Must implement `parse_share_url()` and `parse_video_id()` methods
- Returns standardized `VideoInfo` objects
- Some parsers support both video and image album parsing (e.g., Weibo, Douyin, Kuaishou)
- Image URLs are stored in the `images` field as `ImgInfo` objects

**Video Source Mapping** (`parser/__init__.py`):
- Maps `VideoSource` enum to domain lists and parser classes
- Contains `video_source_info_mapping` dictionary for routing requests
- Provides `parse_video_share_url()` and `parse_video_id()` helper functions

## Development Commands

### Local Development
```bash
# Create and activate virtual environment (Python >= 3.10 required)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000
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
The project uses pytest with comprehensive test coverage:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py
pytest tests/test_base.py
pytest tests/test_routing.py
pytest tests/test_weibo_album.py

# Run tests with coverage
pytest --cov=parser

# Run tests with verbose output
pytest -v

# Run specific test class or method
pytest tests/test_base.py::TestDataClasses
pytest tests/test_base.py::TestDataClasses::test_video_author_creation

# Run tests with markers
pytest -m unit          # Run unit tests only
pytest -m integration   # Run integration tests only
pytest -m "not slow"     # Skip slow tests
```

**Test Structure**: See `tests/README.md` for detailed testing guide including mock strategies and async test patterns.

### Docker
```bash
# Build and run
docker run -d -p 8000:8000 wujunwei928/parse-video-py

# Run with basic auth
docker run -d -p 8000:8000 -e PARSE_VIDEO_USERNAME=username -e PARSE_VIDEO_PASSWORD=password wujunwei928/parse-video-py
```

## API Usage

### Endpoints
- `GET /`: Web interface
- `GET /video/share/url/parse?url=<share_url>`: Parse video from share URL
- `GET /video/id/parse?source=<source>&video_id=<id>`: Parse video by ID

### Basic Auth
Set environment variables to enable authentication:
```bash
export PARSE_VIDEO_USERNAME=username
export PARSE_VIDEO_PASSWORD=password
```

## Adding New Platforms

1. Create new parser class in `parser/` inheriting from `BaseParser`
2. Add enum value to `VideoSource` in `base.py`
3. Update `video_source_info_mapping` in `__init__.py` with domain and parser
4. Implement required abstract methods: `parse_share_url()` and `parse_video_id()`

## Video Data Structure

```python
@dataclasses.dataclass
class VideoInfo:
    video_url: str           # Direct video URL
    cover_url: str           # Video thumbnail
    title: str = ""          # Video title
    music_url: str = ""      # Background music URL
    images: List[ImgInfo] = []  # Image gallery URLs
    author: VideoAuthor = VideoAuthor()  # Author info
```

## MCP Support

The project supports [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) for integration with AI tools:
- MCP endpoint: `http://localhost:8000/mcp`
- Uses StreamableHttp method for AI tool integration
- Enabled via FastAPI-MCP integration in `main.py`

## Important Notes

- All parsers must handle both share URLs and video IDs
- Use `fake_useragent.UserAgent(os=["ios"]).random` for mobile user agents
- Video URLs should be direct, watermark-free when possible
- Error handling should return meaningful messages for unsupported platforms
- The system supports both video and image gallery parsing:
  - Video content: stored in `video_url` field
  - Image albums: stored as list of `ImgInfo` objects in `images` field
- Some platforms (Weibo, Douyin, Kuaishou, Xiaohongshu, Pipixia) support both video and image parsing
- Bilibili parser supports Cookie configuration for higher quality videos (commented out by default)
- Use app share links when possible, desktop web versions may not be fully tested
- Image parsers should prioritize highest quality URLs: large > original > bmiddle > url

## Platform-Specific Implementation Details

**Douyin (抖音) Live Photo Support**:
- Implements specialized slidesinfo API for image galleries with Live Photos
- Detects note content via canonical URLs and HTML patterns
- Extracts both static images and Live Photo video URLs
- Prioritizes non-WebP image formats for better quality
- Supports modal_id parameter for jingxuan page URLs
- Generates required web_id and a_bogus parameters for API calls

**Weibo (微博) Album Parsing**:
- Handles both TV show URLs and regular post URLs
- Supports image galleries with multiple quality levels
- Extracts author information and timestamps
- Handles different URL patterns: `/tv/show/`, `show?fid=`, regular posts

## Parser Implementation Patterns

**For platforms supporting both video and image content:**
- URL routing logic should detect content type and route appropriately
- Video URLs typically contain patterns like `/tv/show/`, `show?fid=`, `/video/`
- Image album URLs are usually regular post URLs that need to be parsed to determine content type
- Implement fallback strategies (mobile API → desktop HTML parsing) for robustness

**For image album parsing:**
- Extract image URLs from platform-specific API responses or HTML
- Return multiple `ImgInfo` objects in the `images` field
- Handle LivePhoto support where applicable (e.g., Douyin, Xiaohongshu)
- For Douyin: Use slidesinfo API with proper authentication parameters
- For Xiaohongshu: Extract LivePhoto URLs from image metadata

## Direct Parser Usage

```python
import asyncio
from parser import parse_video_share_url, parse_video_id, VideoSource

# Parse from share URL
video_info = asyncio.run(parse_video_share_url("share_url"))

# Parse from video ID
video_info = asyncio.run(parse_video_id(VideoSource.DouYin, "video_id"))

# Example: Test parsing with real URLs
```

## Development and Testing

### Authentication and Security
- Basic auth can be enabled via environment variables: `PARSE_VIDEO_USERNAME` and `PARSE_VIDEO_PASSWORD`
- Uses `secrets.compare_digest()` for secure credential comparison
- MCP integration supports AI tool connections at `/mcp` endpoint

### Supported Platforms Summary
- **Video**: 20+ platforms including Douyin, Kuaishou, Weibo, Bilibili, etc.
- **Image Albums**: 5 platforms (Douyin, Kuaishou, Xiaohongshu, Pipixia, Weibo)
- **Live Photos**: Douyin and Xiaohongshu (with platform-specific implementations)

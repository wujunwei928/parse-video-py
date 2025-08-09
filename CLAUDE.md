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
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting

```bash
# Install pre-commit hooks
pre-commit install

# Run formatting tools manually
black .
isort .
flake8 .
```

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

## Important Notes

- All parsers must handle both share URLs and video IDs
- Use `fake_useragent.UserAgent(os=["ios"]).random` for mobile user agents
- Video URLs should be direct, watermark-free when possible
- Error handling should return meaningful messages for unsupported platforms
- The system supports both video and image gallery parsing

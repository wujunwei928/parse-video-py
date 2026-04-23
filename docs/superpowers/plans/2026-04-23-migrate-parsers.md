# QQ/搜狐/CCTV 解析器迁移 + Skill 适配 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Go 项目的腾讯视频、搜狐视频、央视网三个解析器和 analyze-video-url Skill 迁移到本 Python 项目。

**Architecture:** 每个 Go 解析器翻译为继承 `BaseParser` 的 Python 异步类，使用 `httpx.AsyncClient` + 标准 JSON 解析。按 TDD 流程：先写测试 → 实现 → 验证 → 提交。

**Tech Stack:** Python 3.10+, httpx, re, base64, json, pytest

---

## Task 1: 新增 VideoSource 枚举值

**Files:**
- Modify: `src/parse_video_py/parser/base.py:35` (在 `Twitter` 枚举后追加)

- [ ] **Step 1: 在 `VideoSource` 枚举中新增三个值**

在 `src/parse_video_py/parser/base.py` 的 `VideoSource` 枚举末尾（`Twitter` 之后）追加：

```python
    Twitter = "twitter"  # Twitter/X
    QQVideo = "qqvideo"  # 腾讯视频
    Sohu = "sohu"  # 搜狐视频
    CCTV = "cctv"  # 央视网
```

- [ ] **Step 2: 验证枚举可导入**

Run: `cd /code/parse-video-py && source .venv/bin/activate && python -c "from parse_video_py.parser.base import VideoSource; print(VideoSource.QQVideo, VideoSource.Sohu, VideoSource.CCTV)"`
Expected: `VideoSource.QQVideo VideoSource.Sohu VideoSource.CCTV`

- [ ] **Step 3: 提交**

```bash
git add src/parse_video_py/parser/base.py
git commit -m "feat: 新增 QQVideo/Sohu/CCTV VideoSource 枚举值"
```

---

## Task 2: 腾讯视频解析器 — 测试

**Files:**
- Create: `tests/test_qqvideo.py`

- [ ] **Step 1: 编写 QQ 解析器单元测试**

创建 `tests/test_qqvideo.py`：

```python
import pytest

from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.qqvideo import QQVideo


class TestQQVideoExtractVid:
    """测试腾讯视频 ID 提取"""

    def test_pc_page_link(self):
        """PC端 page 链接"""
        qv = QQVideo()
        vid = qv._extract_vid("https://v.qq.com/x/page/l3502vppd13.html")
        assert vid == "l3502vppd13"

    def test_pc_page_with_params(self):
        """PC端 page 带参数"""
        qv = QQVideo()
        vid = qv._extract_vid(
            "https://v.qq.com/x/page/l3502vppd13.html?ptag=v_qq_com"
        )
        assert vid == "l3502vppd13"

    def test_pc_cover_link(self):
        """PC端 cover 链接"""
        qv = QQVideo()
        vid = qv._extract_vid(
            "https://v.qq.com/x/cover/mzc00200mp9v9pw/l3502vppd13.html"
        )
        assert vid == "l3502vppd13"

    def test_pc_cover_with_params(self):
        """PC端 cover 带参数"""
        qv = QQVideo()
        vid = qv._extract_vid(
            "https://v.qq.com/x/cover/mzc00200mp9v9pw/l3502vppd13.html?ptag=v_qq_com"
        )
        assert vid == "l3502vppd13"

    def test_mobile_play_link(self):
        """移动端播放页"""
        qv = QQVideo()
        vid = qv._extract_vid(
            "https://m.v.qq.com/x/m/play?cid=&vid=l3502vppd13&ptag=v_qq_com"
        )
        assert vid == "l3502vppd13"

    def test_invalid_path(self):
        """无效路径"""
        qv = QQVideo()
        with pytest.raises(ValueError):
            qv._extract_vid("https://v.qq.com/x/channel/home")

    def test_mobile_missing_vid(self):
        """移动端缺少vid"""
        qv = QQVideo()
        with pytest.raises(ValueError):
            qv._extract_vid("https://m.v.qq.com/x/m/play?cid=abc")

    def test_empty_string(self):
        """空字符串"""
        qv = QQVideo()
        with pytest.raises(ValueError):
            qv._extract_vid("")


class TestQQVideoVideoSource:
    """测试 VideoSource 枚举"""

    def test_qqvideo_source_exists(self):
        assert VideoSource.QQVideo.value == "qqvideo"
```

- [ ] **Step 2: 运行测试确认失败（模块不存在）**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest tests/test_qqvideo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'parse_video_py.parser.qqvideo'`

---

## Task 3: 腾讯视频解析器 — 实现

**Files:**
- Create: `src/parse_video_py/parser/qqvideo.py`

- [ ] **Step 1: 实现 QQ 解析器**

创建 `src/parse_video_py/parser/qqvideo.py`：

```python
import json
import re
from urllib.parse import parse_qs, urlparse

import httpx

from .base import BaseParser, VideoInfo

# 匹配腾讯视频页面路径中的视频 ID
_qq_vid_path_re = re.compile(r"/x/(?:page|cover)/(?:[^/]+/)?(\w+)\.html")


class QQVideo(BaseParser):
    """
    腾讯视频
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        vid = self._extract_vid(share_url)
        return await self.parse_video_id(vid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        if not video_id:
            raise ValueError("视频ID不能为空")

        api_url = (
            f"https://vv.video.qq.com/getinfo"
            f"?vids={video_id}&platform=101001&otype=json&defn=shd"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=self.get_default_headers())
            response.raise_for_status()

        body = response.text

        # 去除 JSONP 前缀 QZOutputJson= 和尾部分号
        json_str = body.removeprefix("QZOutputJson=").removesuffix(";")

        data = json.loads(json_str)

        # 检查 API 级别错误
        if data.get("em", 0) != 0:
            raise Exception(
                f'腾讯视频API返回错误: {data.get("msg", "")} (em: {data.get("em")})'
            )

        # 检查视频列表
        vi_list = data.get("vl", {}).get("vi", [])
        if not vi_list:
            raise Exception("未找到视频信息，视频可能已被删除或设为私密")

        vi = vi_list[0]

        # 提取 CDN 地址
        ui_list = vi.get("ul", {}).get("ui", [])
        if not ui_list:
            raise Exception("未找到视频CDN地址")

        base_url = ui_list[0].get("url", "")
        fn = vi.get("fn", "")
        fvkey = vi.get("fvkey", "")
        if not base_url or not fn or not fvkey:
            raise Exception("视频地址信息不完整")

        # 构造视频播放地址
        video_url = f"{base_url}{fn}?vkey={fvkey}"

        # 提取视频元信息
        vid = vi.get("vid", "")
        title = vi.get("ti", "")
        cover_url = f"https://puui.qpic.cn/vpic_cover/{vid}/{vid}_hz.jpg/496"

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
        )

    def _extract_vid(self, raw_url: str) -> str:
        """从 URL 中提取腾讯视频 ID"""
        parsed = urlparse(raw_url)
        host = parsed.hostname or ""

        # 移动端播放页: m.v.qq.com/x/m/play?vid={vid}
        if "m.v.qq.com" in host:
            query_params = parse_qs(parsed.query)
            vid = query_params.get("vid", [""])[0]
            if vid:
                return vid
            raise ValueError("移动端链接中未找到vid参数")

        # PC端页面: v.qq.com/x/page/{vid}.html 或 v.qq.com/x/cover/{cid}/{vid}.html
        if "v.qq.com" in host:
            return self._extract_vid_from_path(parsed.path)

        raise ValueError(f"不支持的腾讯视频域名: {host}")

    def _extract_vid_from_path(self, path: str) -> str:
        """从 URL 路径中提取视频 ID"""
        match = _qq_vid_path_re.search(path)
        if match and match.group(1):
            return match.group(1)
        raise ValueError(f"无法从路径 {path} 中提取视频ID")
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest tests/test_qqvideo.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 提交**

```bash
git add src/parse_video_py/parser/qqvideo.py tests/test_qqvideo.py
git commit -m "feat: 新增腾讯视频(QQVideo)解析器及单元测试"
```

---

## Task 4: 搜狐视频解析器 — 测试

**Files:**
- Create: `tests/test_sohu.py`

- [ ] **Step 1: 编写搜狐解析器单元测试**

创建 `tests/test_sohu.py`：

```python
import pytest

from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.sohu import Sohu


class TestSohuExtractVid:
    """测试搜狐视频 ID 提取"""

    def test_base64_encoded_url(self):
        """base64编码URL（解码后为 us/335942214/399571612.shtml）"""
        s = Sohu()
        vid = s._extract_vid(
            "https://tv.sohu.com/v/dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html"
        )
        assert vid == "399571612"

    def test_direct_path_url(self):
        """直接路径URL"""
        s = Sohu()
        vid = s._extract_vid("http://my.tv.sohu.com/us/335942214/399571612.shtml")
        assert vid == "399571612"

    def test_invalid_url(self):
        """无效URL"""
        s = Sohu()
        with pytest.raises(ValueError):
            s._extract_vid("https://tv.sohu.com/v/invalid.html")

    def test_non_sohu_link(self):
        """非搜狐链接"""
        s = Sohu()
        with pytest.raises(ValueError):
            s._extract_vid("https://www.douyin.com/video/123")


class TestSohuExtractVidFromPath:
    """测试从解码路径提取视频 ID"""

    def test_standard_path(self):
        s = Sohu()
        vid = s._extract_vid_from_path("us/335942214/399571612.shtml")
        assert vid == "399571612"

    def test_path_with_leading_slash(self):
        s = Sohu()
        vid = s._extract_vid_from_path("/us/335942214/399571612.shtml")
        assert vid == "399571612"

    def test_invalid_path(self):
        s = Sohu()
        with pytest.raises(ValueError):
            s._extract_vid_from_path("invalid/path")


class TestSohuVideoSource:
    """测试 VideoSource 枚举"""

    def test_sohu_source_exists(self):
        assert VideoSource.Sohu.value == "sohu"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest tests/test_sohu.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'parse_video_py.parser.sohu'`

---

## Task 5: 搜狐视频解析器 — 实现

**Files:**
- Create: `src/parse_video_py/parser/sohu.py`

- [ ] **Step 1: 实现搜狐解析器**

创建 `src/parse_video_py/parser/sohu.py`：

```python
import base64
import json
import re

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo

# 匹配 tv.sohu.com/v/{base64}.html 格式的路径
_sohu_base64_vid_re = re.compile(r"/v/([A-Za-z0-9+/=]+)\.html")

# 匹配 us/{uid}/{vid}.shtml 格式的路径
_sohu_user_vid_re = re.compile(r"/?us/\d+/(\d+)\.shtml")


class Sohu(BaseParser):
    """
    搜狐视频
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        vid = self._extract_vid(share_url)
        return await self.parse_video_id(vid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        if not video_id:
            raise ValueError("视频ID不能为空")

        api_url = (
            f"https://api.tv.sohu.com/v4/video/info/{video_id}.json"
            f"?site=2&api_key=9854b2afa779e1a6bcdd07b217417549&sver=6.2.0"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=self.get_default_headers())
            response.raise_for_status()

        data = response.json()

        # 检查API状态
        if data.get("status") != 200:
            raise Exception(
                f'搜狐视频API返回错误: {data.get("statusText", "")} '
                f'(status: {data.get("status")})'
            )

        video_data = data.get("data")
        if not video_data:
            raise Exception("API响应中未找到视频数据")

        # 提取视频播放地址
        video_url = video_data.get("url_high_mp4", "") or video_data.get(
            "download_url", ""
        )
        if not video_url:
            raise Exception("未找到视频播放地址")

        # 提取视频元信息
        title = video_data.get("video_name", "")
        cover_url = video_data.get("originalCutCover", "")

        # 提取作者信息
        user_info = video_data.get("user", {})
        author = VideoAuthor(
            uid=str(user_info.get("user_id", "")),
            name=user_info.get("nickname", ""),
            avatar=user_info.get("small_pic", ""),
        )

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=author,
        )

    def _extract_vid(self, raw_url: str) -> str:
        """从 URL 中提取搜狐视频 ID"""
        # 匹配 tv.sohu.com/v/{base64}.html 格式
        match = _sohu_base64_vid_re.search(raw_url)
        if match:
            decoded = base64.b64decode(match.group(1)).decode("utf-8")
            return self._extract_vid_from_path(decoded)

        # 匹配 my.tv.sohu.com/us/{uid}/{vid}.shtml 格式
        if "my.tv.sohu.com" in raw_url or "tv.sohu.com/us/" in raw_url:
            return self._extract_vid_from_path(raw_url)

        raise ValueError("不是有效的搜狐视频链接")

    def _extract_vid_from_path(self, path: str) -> str:
        """从路径中提取视频 ID（适配 us/{uid}/{vid}.shtml 格式）"""
        match = _sohu_user_vid_re.search(path)
        if match and match.group(1):
            return match.group(1)
        raise ValueError(f"无法从路径 {path} 中提取视频ID")
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest tests/test_sohu.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 提交**

```bash
git add src/parse_video_py/parser/sohu.py tests/test_sohu.py
git commit -m "feat: 新增搜狐视频(Sohu)解析器及单元测试"
```

---

## Task 6: 央视网解析器 — 测试

**Files:**
- Create: `tests/test_cctv.py`

- [ ] **Step 1: 编写 CCTV 解析器单元测试**

创建 `tests/test_cctv.py`：

```python
import pytest

from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.cctv import CCTV


class TestCCTVExtractGuid:
    """测试从 HTML 中提取 GUID"""

    def test_standard_format(self):
        """标准格式"""
        html = '<script>var guid = "68c27e1af8cc47f79000ca944432b0e6";</script>'
        guid = CCTV._extract_guid_from_html(html)
        assert guid == "68c27e1af8cc47f79000ca944432b0e6"

    def test_no_spaces(self):
        """无空格"""
        html = '<script>var guid="abc123def456";</script>'
        guid = CCTV._extract_guid_from_html(html)
        assert guid == "abc123def456"

    def test_multiple_spaces(self):
        """多空格"""
        html = '<script>var  guid  =  "multiSpaceGuid";</script>'
        guid = CCTV._extract_guid_from_html(html)
        assert guid == "multiSpaceGuid"

    def test_page_no_guid(self):
        """页面无GUID"""
        html = "<html><body>no guid here</body></html>"
        with pytest.raises(ValueError):
            CCTV._extract_guid_from_html(html)

    def test_empty_guid(self):
        """空GUID"""
        html = '<script>var guid = "";</script>'
        with pytest.raises(ValueError):
            CCTV._extract_guid_from_html(html)


class TestCCTVVideoSource:
    """测试 VideoSource 枚举"""

    def test_cctv_source_exists(self):
        assert VideoSource.CCTV.value == "cctv"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest tests/test_cctv.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'parse_video_py.parser.cctv'`

---

## Task 7: 央视网解析器 — 实现

**Files:**
- Create: `src/parse_video_py/parser/cctv.py`

- [ ] **Step 1: 实现 CCTV 解析器**

创建 `src/parse_video_py/parser/cctv.py`：

```python
import json
import re

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo

# 匹配央视网页面中嵌入的视频 GUID
_cctv_guid_re = re.compile(r'var\s+guid\s*=\s*"([^"]+)"')


class CCTV(BaseParser):
    """
    央视网
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        # 请求页面 HTML 提取视频 GUID
        guid = await self._extract_guid(share_url)
        return await self.parse_video_id(guid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        if not video_id:
            raise ValueError("视频GUID不能为空")

        api_url = (
            f"https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={video_id}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=self.get_default_headers())
            response.raise_for_status()

        data = response.json()

        # 检查 API 状态
        status = data.get("status", "")
        if status != "001":
            raise Exception(
                f'央视网视频API返回错误 (status: {status}, '
                f'title: {data.get("title", "")})'
            )

        # 提取 HLS 视频播放地址
        # 注：manifest 中的 h5e/enc/enc2 高码率流在 H.264 帧级加扰，播放花屏，仅 hls_url 可正常播放
        video_url = data.get("hls_url", "")
        if not video_url:
            raise Exception("未找到视频播放地址")

        # 提取视频元信息
        title = data.get("title", "")
        cover_url = data.get("image", "")
        play_channel = data.get("play_channel", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(name=play_channel),
        )

    async def _extract_guid(self, page_url: str) -> str:
        """从页面 URL 请求并提取视频 GUID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(page_url, headers=self.get_default_headers())
            response.raise_for_status()

        return self._extract_guid_from_html(response.text)

    @staticmethod
    def _extract_guid_from_html(html: str) -> str:
        """从 HTML 字符串中提取视频 GUID"""
        match = _cctv_guid_re.search(html)
        if match and match.group(1):
            return match.group(1)
        raise ValueError("页面中未找到视频GUID")
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest tests/test_cctv.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 提交**

```bash
git add src/parse_video_py/parser/cctv.py tests/test_cctv.py
git commit -m "feat: 新增央视网(CCTV)解析器及单元测试"
```

---

## Task 8: 注册解析器到映射表

**Files:**
- Modify: `src/parse_video_py/parser/__init__.py`

- [ ] **Step 1: 添加 import 和映射条目**

在 `src/parse_video_py/parser/__init__.py` 中：

1. 在 import 区域（第 1-23 行），按字母序插入三个新 import：
```python
from .cctv import CCTV
```
（在 `.base` 之后）

```python
from .qqvideo import QQVideo
```
（在 `.pipixia` 之后）

```python
from .sohu import Sohu
```
（在 `.sixroom` 之后）

2. 在 `video_source_info_mapping` 字典中，按字母序插入三个新条目：

在 `AcFun` 条目之后插入：
```python
    VideoSource.CCTV: {
        "domain_list": ["tv.cctv.cn", "tv.cctv.com"],
        "parser": CCTV,
    },
```

在 `QuanMinKGe` 条目之后插入：
```python
    VideoSource.QQVideo: {
        "domain_list": ["v.qq.com"],
        "parser": QQVideo,
    },
```

在 `SixRoom` 条目之后插入：
```python
    VideoSource.Sohu: {
        "domain_list": ["tv.sohu.com", "my.tv.sohu.com"],
        "parser": Sohu,
    },
```

- [ ] **Step 2: 运行全量测试验证无回归**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest -v`
Expected: 全部 PASS（包括新增和已有的测试）

- [ ] **Step 3: 提交**

```bash
git add src/parse_video_py/parser/__init__.py
git commit -m "feat: 注册 QQVideo/Sohu/CCTV 解析器到映射表"
```

---

## Task 9: 适配 analyze-video-url Skill

**Files:**
- Create: `.claude/skills/analyze-video-url/SKILL.md`

- [ ] **Step 1: 创建适配后的 Skill 文件**

将 Go 项目的 `.claude/skills/analyze-video-url/SKILL.md` 复制到 Python 项目的相同路径，并做以下适配：

**路径引用替换：**
- `parser/vars.go` → `parser/__init__.py`（映射注册）
- `parser/parser.go:28` → `parser/__init__.py`（`parse_video_share_url` 函数）
- `utils/utils.go:9` → `utils.py`（URL 提取正则）
- 所有 `parser/*.go` 文件引用 → 对应 `parser/*.py`
- 行号引用去掉，改为函数名引用

**数据结构替换：**
- `VideoParseInfo` → `VideoInfo`
- `VideoShareUrlDomain` → `domain_list`
- `videoSourceInfoMapping` → `video_source_info_mapping`
- `Source*` 常量 → `VideoSource.*` 枚举

**工具链替换：**
- `resty` / `net/http` → `httpx.AsyncClient`
- `gjson.Get()` → 标准 JSON 字典访问
- `encoding/json` → `json` 标准库
- `NoRedirectPolicy` → `follow_redirects=False`

**解析器模板替换（步骤 5 生成代码部分）：**
- `type <platform> struct{}` → `class <Platform>(BaseParser):`
- `func (x type) parseShareUrl(...)` → `async def parse_share_url(self, ...)`
- `func (x type) parseVideoID(...)` → `async def parse_video_id(self, ...)`
- import 风格从 Go 改为 Python（`from .base import BaseParser, VideoInfo`）

**测试模板替换：**
- `parser/<platform>_test.go` → `tests/test_<platform>.py`
- `go test` → `pytest`
- Go table-driven test → pytest class + method

**构建/验证命令替换：**
- `go build ./...` → `pytest -v`
- `go test ./parser/...` → `pytest tests/ -v`

**文件清单替换：**
- `parser/vars.go` → `parser/__init__.py` + `parser/base.py`
- `cmd/handlers.go` → 去掉（Python 项目没有此文件）
- `README.md` → 保留（如有平台列表需更新）

核心分析流程（步骤 1-4、Red Flags、常见错误）的逻辑和判断规则保持不变。

- [ ] **Step 2: 提交**

```bash
git add .claude/skills/analyze-video-url/SKILL.md
git commit -m "feat: 适配 analyze-video-url Skill 到 Python 项目"
```

---

## Task 10: 最终验证

- [ ] **Step 1: 运行全量测试套件**

Run: `cd /code/parse-video-py && source .venv/bin/activate && pytest -v`
Expected: 全部 PASS，无失败、无跳过

- [ ] **Step 2: 运行代码格式检查**

Run: `cd /code/parse-video-py && source .venv/bin/activate && black --check . && isort --check . && flake8 .`
Expected: 全部通过

- [ ] **Step 3: 验证导入链完整**

Run: `cd /code/parse-video-py && source .venv/bin/activate && python -c "from parse_video_py.parser import parse_video_share_url; print('OK')"`
Expected: `OK`

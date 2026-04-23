import pytest

from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.sohu import Sohu


class TestSohuExtractVid:
    """测试搜狐视频 ID 提取"""

    def test_base64_encoded_url(self):
        """base64编码URL"""
        s = Sohu()
        vid = s._extract_vid(
            "https://tv.sohu.com/v/" "dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html"
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


class TestSohuParseVideoId:
    """测试 parse_video_id 响应解析（mock httpx）"""

    @pytest.fixture
    def mock_sohu_response(self, monkeypatch):
        """mock 成功响应"""

        async def mock_get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {
                        "status": 200,
                        "data": {
                            "video_name": "搜狐测试视频",
                            "url_high_mp4": ("https://data.vod.itc.cn/test.mp4"),
                            "originalCutCover": ("https://pic.sohu.com/cover.jpg"),
                            "user": {
                                "user_id": 335942214,
                                "nickname": "测试用户",
                                "small_pic": ("https://pic.sohu.com/avatar.jpg"),
                            },
                        },
                    }

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    @pytest.mark.asyncio
    async def test_parse_video_id_success(self, mock_sohu_response):
        """测试成功解析搜狐视频响应"""
        s = Sohu()
        result = await s.parse_video_id("399571612")
        assert result.video_url == ("https://data.vod.itc.cn/test.mp4")
        assert result.title == "搜狐测试视频"
        assert result.author.name == "测试用户"
        assert result.author.uid == "335942214"

    @pytest.mark.asyncio
    async def test_parse_video_id_api_error(self, monkeypatch):
        """测试 API 返回错误状态"""

        async def mock_get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {
                        "status": 404,
                        "statusText": "视频不存在",
                    }

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        s = Sohu()
        with pytest.raises(Exception, match="搜狐视频API返回错误"):
            await s.parse_video_id("invalid_id")

    @pytest.mark.asyncio
    async def test_parse_video_id_fallback_url(self, monkeypatch):
        """测试 url_high_mp4 为空时回退到 download_url"""

        async def mock_get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {
                        "status": 200,
                        "data": {
                            "video_name": "回退测试",
                            "url_high_mp4": "",
                            "download_url": ("https://data.vod.itc.cn/fallback.mp4"),
                            "originalCutCover": "",
                            "user": {},
                        },
                    }

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        s = Sohu()
        result = await s.parse_video_id("123")
        assert result.video_url == ("https://data.vod.itc.cn/fallback.mp4")

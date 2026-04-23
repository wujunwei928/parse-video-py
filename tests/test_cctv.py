import pytest

from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.cctv import CCTV


class TestCCTVExtractGuid:
    """测试从 HTML 中提取 GUID"""

    def test_standard_format(self):
        """标准格式"""
        html = "<script>var guid = " '"68c27e1af8cc47f79000ca944432b0e6";</script>'
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


class TestCCTVParseVideoId:
    """测试 parse_video_id 响应解析（mock httpx）"""

    @pytest.mark.asyncio
    async def test_parse_video_id_success(self, monkeypatch):
        """测试成功解析央视网视频响应"""

        async def mock_get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {
                        "status": "001",
                        "hls_url": ("https://hls.cctv.cn/test.m3u8"),
                        "title": "新闻联播",
                        "image": ("https://p1.img.cctv.cn/cover.jpg"),
                        "play_channel": "CCTV-1",
                    }

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        c = CCTV()
        result = await c.parse_video_id("68c27e1af8cc47f79000ca944432b0e6")
        assert result.video_url == ("https://hls.cctv.cn/test.m3u8")
        assert result.title == "新闻联播"
        assert result.author.name == "CCTV-1"

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
                        "status": "002",
                        "title": "视频已删除",
                    }

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        c = CCTV()
        with pytest.raises(Exception, match="央视网视频API返回错误"):
            await c.parse_video_id("invalid_guid")

    @pytest.mark.asyncio
    async def test_parse_video_id_no_hls_url(self, monkeypatch):
        """测试 hls_url 为空"""

        async def mock_get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {"status": "001", "hls_url": ""}

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        c = CCTV()
        with pytest.raises(Exception, match="未找到视频播放地址"):
            await c.parse_video_id("some_guid")

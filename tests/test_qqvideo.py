import json

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
            "https://v.qq.com/x/page/l3502vppd13.html" "?ptag=v_qq_com"
        )
        assert vid == "l3502vppd13"

    def test_pc_cover_link(self):
        """PC端 cover 链接"""
        qv = QQVideo()
        vid = qv._extract_vid(
            "https://v.qq.com/x/cover/mzc00200mp9v9pw" "/l3502vppd13.html"
        )
        assert vid == "l3502vppd13"

    def test_pc_cover_with_params(self):
        """PC端 cover 带参数"""
        qv = QQVideo()
        vid = qv._extract_vid(
            "https://v.qq.com/x/cover/mzc00200mp9v9pw" "/l3502vppd13.html?ptag=v_qq_com"
        )
        assert vid == "l3502vppd13"

    def test_mobile_play_link(self):
        """移动端播放页"""
        qv = QQVideo()
        vid = qv._extract_vid(
            "https://m.v.qq.com/x/m/play" "?cid=&vid=l3502vppd13&ptag=v_qq_com"
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


class TestQQVideoParseVideoId:
    """测试 parse_video_id 响应解析（mock httpx）"""

    @pytest.fixture
    def mock_qq_response(self, monkeypatch):
        """mock httpx.AsyncClient.get 返回腾讯视频 API 响应"""

        async def mock_get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                @property
                def text(self):
                    return (
                        "QZOutputJson="
                        + json.dumps(
                            {
                                "em": 0,
                                "vl": {
                                    "vi": [
                                        {
                                            "vid": "l3502vppd13",
                                            "ti": "测试视频标题",
                                            "fn": "l3502vppd13.mp4",
                                            "fvkey": "test_vkey_123",
                                            "ul": {
                                                "ui": [
                                                    {
                                                        "url": (
                                                            "https://vgg"
                                                            ".video.qq.com/"
                                                        )
                                                    }
                                                ]
                                            },
                                        }
                                    ]
                                },
                            }
                        )
                        + ";"
                    )

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    @pytest.mark.asyncio
    async def test_parse_video_id_success(self, mock_qq_response):
        """测试成功解析腾讯视频响应"""
        qv = QQVideo()
        result = await qv.parse_video_id("l3502vppd13")
        assert result.video_url == (
            "https://vgg.video.qq.com/l3502vppd13.mp4" "?vkey=test_vkey_123"
        )
        assert result.title == "测试视频标题"
        assert "l3502vppd13" in result.cover_url

    @pytest.mark.asyncio
    async def test_parse_video_id_api_error(self, monkeypatch):
        """测试 API 返回错误码"""

        async def mock_get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                @property
                def text(self):
                    return (
                        "QZOutputJson=" + json.dumps({"em": 100, "msg": "视频不存在"}) + ";"
                    )

            return MockResponse()

        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        qv = QQVideo()
        with pytest.raises(Exception, match="腾讯视频API返回错误"):
            await qv.parse_video_id("invalid_vid")

    @pytest.mark.asyncio
    async def test_parse_video_id_empty(self):
        """测试空视频 ID"""
        qv = QQVideo()
        with pytest.raises(ValueError, match="视频ID不能为空"):
            await qv.parse_video_id("")

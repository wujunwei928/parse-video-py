import os
from unittest.mock import patch

from parse_video_py.utils import create_async_client, extract_url


class TestCreateAsyncClient:
    """测试代理客户端工厂函数"""

    def test_no_proxy_env(self):
        """未设置代理环境变量时，httpx.AsyncClient 不传 proxy 参数"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client()
                mock.assert_called_once_with()

    def test_with_proxy_env(self):
        """设置代理环境变量后，proxy 参数被注入"""
        proxy_url = "http://user:pass@proxy.example.com:8080"
        with patch.dict(os.environ, {"PARSE_VIDEO_PROXY": proxy_url}):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client()
                mock.assert_called_once_with(proxy=proxy_url)

    def test_proxy_with_follow_redirects(self):
        """代理和 follow_redirects 参数可共存"""
        proxy_url = "http://proxy.example.com:8080"
        with patch.dict(os.environ, {"PARSE_VIDEO_PROXY": proxy_url}):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client(follow_redirects=True)
                mock.assert_called_once_with(proxy=proxy_url, follow_redirects=True)

    def test_existing_kwargs_preserved(self):
        """未设代理时，透传的 kwargs 不变"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client(follow_redirects=False)
                mock.assert_called_once_with(follow_redirects=False)


class TestExtractUrl:
    """测试 URL 提取工具函数"""

    def test_sohu_base64_url(self):
        """搜狐 base64 编码 URL 不被截断"""
        url = "https://tv.sohu.com/v/" "dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html"
        assert extract_url(url) == url

    def test_sohu_base64_in_text(self):
        """从混合文本中提取搜狐 base64 URL"""
        text = (
            "看看这个 https://tv.sohu.com/v/"
            "dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html 好看"
        )
        expected = (
            "https://tv.sohu.com/v/" "dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html"
        )
        assert extract_url(text) == expected

    def test_regular_url(self):
        """常规 URL 不受影响"""
        url = "https://v.douyin.com/abc123"
        assert extract_url(url) == url

    def test_url_with_query_params(self):
        """带查询参数的 URL"""
        url = "https://v.qq.com/x/page/l3502vppd13.html?ptag=v_qq_com"
        assert extract_url(url) == url

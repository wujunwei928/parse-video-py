import os
from unittest.mock import patch

from parse_video_py.outbound import CheckedAsyncTransport
from parse_video_py.parser.base import VideoSource
from parse_video_py.utils import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_TIMEOUT,
    create_async_client,
    extract_url,
)


class TestCreateAsyncClient:
    """测试代理/超时/出站边界客户端工厂函数"""

    def test_no_proxy_env(self):
        """未设置代理环境变量时，httpx.AsyncClient 不传 proxy 参数，但有默认超时与重定向上限"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client()
                mock.assert_called_once_with(
                    timeout=DEFAULT_TIMEOUT,
                    max_redirects=DEFAULT_MAX_REDIRECTS,
                    trust_env=False,
                )

    def test_with_proxy_env(self):
        """设置代理环境变量后，proxy 参数被注入"""
        proxy_url = "http://user:pass@proxy.example.com:8080"
        with patch.dict(os.environ, {"PARSE_VIDEO_PROXY": proxy_url}):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client()
                mock.assert_called_once_with(
                    proxy=proxy_url,
                    timeout=DEFAULT_TIMEOUT,
                    max_redirects=DEFAULT_MAX_REDIRECTS,
                    trust_env=False,
                )

    def test_proxy_with_follow_redirects(self):
        """代理和 follow_redirects 参数可共存"""
        proxy_url = "http://proxy.example.com:8080"
        with patch.dict(os.environ, {"PARSE_VIDEO_PROXY": proxy_url}):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client(follow_redirects=True)
                mock.assert_called_once_with(
                    proxy=proxy_url,
                    follow_redirects=True,
                    timeout=DEFAULT_TIMEOUT,
                    max_redirects=DEFAULT_MAX_REDIRECTS,
                    trust_env=False,
                )

    def test_existing_kwargs_preserved(self):
        """未设代理时，透传的 kwargs 不变；显式 timeout 可覆盖默认值"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client(follow_redirects=False)
                mock.assert_called_once_with(
                    follow_redirects=False,
                    timeout=DEFAULT_TIMEOUT,
                    max_redirects=DEFAULT_MAX_REDIRECTS,
                    trust_env=False,
                )
                mock.reset_mock()
                create_async_client(timeout=5.0)
                mock.assert_called_once_with(
                    timeout=5.0,
                    max_redirects=DEFAULT_MAX_REDIRECTS,
                    trust_env=False,
                )

    def test_source_attaches_checked_transport(self):
        """传入 source 时挂载出站边界 transport，代理由 transport 内部处理"""
        proxy_url = "http://proxy.example.com:8080"
        with patch.dict(os.environ, {"PARSE_VIDEO_PROXY": proxy_url}):
            with patch("parse_video_py.utils.httpx.AsyncClient") as mock:
                create_async_client(source=VideoSource.Sohu)
                kwargs = mock.call_args.kwargs
                assert isinstance(kwargs["transport"], CheckedAsyncTransport)
                assert kwargs["transport"]._proxy == proxy_url
                assert "proxy" not in kwargs  # 避免与 transport 冲突


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

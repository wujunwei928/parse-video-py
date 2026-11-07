"""出站边界（outbound 模块）安全测试。

覆盖：域名伪装/后缀冒充/回环与特殊网段/端口与 userinfo 校验、
重定向每一跳白名单、跨主机敏感头剥离、响应大小限制。
对齐 Go 版 parser/outbound_test.go 的场景。
"""

import ipaddress

import httpx
import pytest

from parse_video_py import outbound
from parse_video_py.outbound import (
    CheckedAsyncTransport,
    OutboundError,
    ResponseTooLargeError,
    host_matches,
    http_hostname,
    public_address,
)
from parse_video_py.parser import share_url_source
from parse_video_py.parser.base import VideoSource


class TestHostMatches:
    """DNS 标签边界匹配：拒绝子串伪装"""

    @pytest.mark.parametrize(
        "host,domain,expected",
        [
            ("weibo.com", "weibo.com", True),
            ("www.weibo.com", "weibo.com", True),
            ("m.weibo.cn", "weibo.cn", True),
            ("evilweibo.com", "weibo.com", False),  # 标签前缀伪装
            ("weibo.com.evil.com", "weibo.com", False),  # 后缀冒充
            ("evil.com", "weibo.com", False),
        ],
    )
    def test_host_matches(self, host, domain, expected):
        assert host_matches(host, domain) is expected


class TestHttpHostname:
    """URL 形态校验：协议/端口/userinfo"""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.douyin.com/video/1", "www.douyin.com"),
            ("http://v.qq.com/x/page/1.html", "v.qq.com"),
            ("https://v.douyin.com:443/abc/", "v.douyin.com"),
            ("http://v.douyin.com:80/abc/", "v.douyin.com"),
            ("https://V.DouYin.COM/abc/", "v.douyin.com"),
            ("https://v.douyin.com./abc/", "v.douyin.com"),
            ("https://v.douyin.com:8080/abc/", None),  # 非默认端口
            ("http://weibo.com@127.0.0.1/a", None),  # userinfo
            ("ftp://v.douyin.com/abc", None),  # 非 http(s)
            ("notaurl", None),
            ("", None),
        ],
    )
    def test_http_hostname(self, url, expected):
        assert http_hostname(url) == expected

    def test_httpx_url_input(self):
        assert http_hostname(httpx.URL("https://www.douyin.com/video/1")) == (
            "www.douyin.com"
        )
        assert http_hostname(httpx.URL("https://u:p@www.douyin.com/")) is None


class TestPublicAddress:
    """公网 IP 判定：拒绝私网/回环/链路本地/特殊用途网段"""

    @pytest.mark.parametrize(
        "addr",
        [
            "8.8.8.8",
            "1.1.1.1",
            "2606:4700::1111",
        ],
    )
    def test_public(self, addr):
        assert public_address(ipaddress.ip_address(addr)) is True

    @pytest.mark.parametrize(
        "addr",
        [
            "127.0.0.1",
            "10.0.0.1",
            "192.168.1.1",
            "172.16.0.1",
            "169.254.169.254",  # 云元数据
            "100.64.0.1",  # CGNAT
            "0.0.0.0",
            "192.0.2.1",  # TEST-NET
            "198.18.0.1",
            "240.0.0.1",
            "::1",
            "fe80::1",
            "fd00::1",
            "2001:db8::1",
            "2002:0102:0304::1",  # 6to4
            "::ffff:127.0.0.1",  # IPv4-mapped 回环
            "::ffff:10.0.0.1",  # IPv4-mapped 私网
        ],
    )
    def test_not_public(self, addr):
        assert public_address(ipaddress.ip_address(addr)) is False


class TestResolvePublicHost:
    """DNS 解析结果必须全部为公网地址"""

    @pytest.mark.asyncio
    async def test_resolves_to_private_rejected(self, monkeypatch):
        def fake_getaddrinfo(host, port):
            return [(2, 0, 0, "", ("192.168.1.10", 0))]

        monkeypatch.setattr(outbound.socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(OutboundError):
            await outbound.resolve_public_host("internal.example")

    @pytest.mark.asyncio
    async def test_all_addresses_must_be_public(self, monkeypatch):
        def fake_getaddrinfo(host, port):
            # 一个公网 + 一个私网：整体拒绝
            return [
                (2, 0, 0, "", ("8.8.8.8", 0)),
                (2, 0, 0, "", ("10.0.0.2", 0)),
            ]

        monkeypatch.setattr(outbound.socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(OutboundError):
            await outbound.resolve_public_host("mixed.example")

    @pytest.mark.asyncio
    async def test_public_addresses_pass(self, monkeypatch):
        def fake_getaddrinfo(host, port):
            return [(2, 0, 0, "", ("8.8.8.8", 0))]

        monkeypatch.setattr(outbound.socket, "getaddrinfo", fake_getaddrinfo)
        await outbound.resolve_public_host("ok.example")

    @pytest.mark.asyncio
    async def test_ip_literal_private_rejected(self):
        with pytest.raises(OutboundError):
            await outbound.resolve_public_host("127.0.0.1")


class TestShareUrlSource:
    """平台路由：host 后缀最长匹配，拒绝子串伪装与 userinfo"""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://v.douyin.com/abc123/", VideoSource.DouYin),
            ("https://www.iesdouyin.com/share/video/1", VideoSource.DouYin),
            ("https://www.bilibili.com/video/BV1xx", VideoSource.BiliBili),
            ("https://b23.tv/abc123", VideoSource.BiliBili),
            ("https://weibo.com/tv/show/1", VideoSource.WeiBo),
            ("https://m.weibo.cn/status/Abc123", VideoSource.LvZhou),
            ("https://xhslink.cn/abc123", VideoSource.RedBook),
            ("https://www.xiaohongshu.com/explore/1", VideoSource.RedBook),
            ("https://t.co/abc123", VideoSource.Twitter),
        ],
    )
    def test_known_platforms(self, url, expected):
        assert share_url_source(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.com/?x=weibo.com",  # 子串伪装
            "https://weibo.com.evil.com/a",  # 后缀冒充
            "http://weibo.com@127.0.0.1:8080/a/b",  # userinfo + 端口
            "https://v.douyin.com:8080/abc/",  # 非默认端口
            "https://unknown.example.com/video/1",
            "not a url",
        ],
    )
    def test_unsupported_rejected(self, url):
        from parse_video_py.parser import UnsupportedShareUrlError

        with pytest.raises(UnsupportedShareUrlError):
            share_url_source(url)


def _mock_inner(handler):
    return httpx.MockTransport(handler)


def _request(url, headers=None):
    return httpx.Request("GET", url, headers=headers or {})


class TestCheckedAsyncTransport:
    """每一跳请求都过白名单 + 敏感头剥离 + 响应大小限制"""

    def _transport(self, handler, **kwargs):
        transport = CheckedAsyncTransport(
            source=VideoSource.WeiBo, max_response_bytes=1024, **kwargs
        )
        transport._inner = _mock_inner(handler)
        return transport

    @pytest.mark.asyncio
    async def test_allowed_host_passes(self, monkeypatch):
        async def fake_resolve(host):
            return None

        monkeypatch.setattr(outbound, "resolve_public_host", fake_resolve)
        seen = []

        def handler(request):
            seen.append(str(request.url))
            return httpx.Response(200, content=b"ok")

        transport = self._transport(handler)
        response = await transport.handle_async_request(
            _request("https://weibo.com/tv/show/1")
        )
        assert response.status_code == 200
        assert await response.aread() == b"ok"
        assert seen == ["https://weibo.com/tv/show/1"]

    @pytest.mark.asyncio
    async def test_disallowed_host_rejected(self):
        transport = self._transport(lambda request: httpx.Response(200))
        with pytest.raises(OutboundError):
            await transport.handle_async_request(
                _request("https://internal.example/secret")
            )

    @pytest.mark.asyncio
    async def test_disallowed_redirect_hop_rejected(self, monkeypatch):
        """重定向跳到白名单外主机的第二跳必须被拒绝"""
        transport = self._transport(lambda request: httpx.Response(302))

        # 第一跳：允许的分享域名（绕过 DNS 校验以便单测）
        async def fake_resolve(host):
            return None

        monkeypatch.setattr(outbound, "resolve_public_host", fake_resolve)
        await transport.handle_async_request(_request("https://weibo.com/tv/show/1"))
        # 第二跳：httpx 跟随重定向生成的新请求走同一 transport
        with pytest.raises(OutboundError):
            await transport.handle_async_request(
                _request("http://169.254.169.254/latest/meta-data/")
            )

    @pytest.mark.asyncio
    async def test_cross_host_strips_sensitive_headers(self, monkeypatch):
        """跨主机请求剥离 Cookie/Authorization/Referer"""
        captured = {}

        def handler(request):
            captured[str(request.url)] = dict(request.headers)
            return httpx.Response(200)

        async def fake_resolve(host):
            return None

        monkeypatch.setattr(outbound, "resolve_public_host", fake_resolve)
        transport = self._transport(handler)
        headers = {
            "Cookie": "session=secret",
            "Authorization": "Bearer token",
            "Referer": "https://weibo.com/tv/show/1",
            "X-Custom": "keep-me",
        }
        await transport.handle_async_request(
            _request("https://weibo.com/tv/show/1", headers=headers)
        )
        second = await transport.handle_async_request(
            _request("https://m.weibo.cn/status/1", headers=headers)
        )
        assert second.status_code == 200
        second_headers = captured["https://m.weibo.cn/status/1"]
        assert "cookie" not in second_headers
        assert "authorization" not in second_headers
        assert "referer" not in second_headers
        assert second_headers["x-custom"] == "keep-me"

    @pytest.mark.asyncio
    async def test_content_length_over_limit_rejected(self):
        def handler(request):
            return httpx.Response(
                200, headers={"content-length": str(1024 * 1024 * 32)}, content=b""
            )

        transport = self._transport(handler)
        with pytest.raises(ResponseTooLargeError):
            await transport.handle_async_request(_request("https://weibo.com/a"))

    @pytest.mark.asyncio
    async def test_stream_over_limit_rejected(self, monkeypatch):
        """没有 content-length 时由流式计数兜底"""

        class BigStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                for _ in range(20):
                    yield b"x" * 100  # 共 2000 字节 > 1024 上限

        def handler(request):
            return httpx.Response(200, stream=BigStream())

        async def fake_resolve(host):
            return None

        monkeypatch.setattr(outbound, "resolve_public_host", fake_resolve)
        transport = self._transport(handler)
        response = await transport.handle_async_request(_request("https://weibo.com/a"))
        with pytest.raises(ResponseTooLargeError):
            await response.aread()

    @pytest.mark.asyncio
    async def test_proxy_mode_skips_dns_check(self, monkeypatch):
        """配置代理时不做本地 DNS 校验，由代理负责出口"""

        def boom_resolve(host):
            raise AssertionError("代理模式不应做本地 DNS 校验")

        monkeypatch.setattr(outbound, "resolve_public_host", boom_resolve)
        transport = CheckedAsyncTransport(
            source=VideoSource.WeiBo,
            proxy="http://proxy.example.com:8080",
            max_response_bytes=1024,
        )
        transport._inner = _mock_inner(
            lambda request: httpx.Response(200, content=b"ok")
        )
        response = await transport.handle_async_request(
            _request("https://weibo.com/tv/show/1")
        )
        assert await response.aread() == b"ok"


class TestAllowedHosts:
    """平台白名单 = 分享域名 + 上游域名"""

    def test_sohu_includes_upstream(self):
        hosts = outbound.allowed_hosts(VideoSource.Sohu)
        assert "tv.sohu.com" in hosts
        assert "my.tv.sohu.com" in hosts

    def test_qqvideo_includes_api_and_cover_hosts(self):
        hosts = outbound.allowed_hosts(VideoSource.QQVideo)
        assert "vv.video.qq.com" in hosts
        assert "puui.qpic.cn" in hosts

    def test_douyin_redirect_domains_allowed(self):
        hosts = outbound.allowed_hosts(VideoSource.DouYin)
        assert "iesdouyin.com" in hosts
        assert host_matches("www.iesdouyin.com", "iesdouyin.com")

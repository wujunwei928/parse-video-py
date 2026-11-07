"""出站请求边界：平台域名白名单、公网 IP 校验与响应大小限制。

对齐 Go 版 parse-video 的 parser/outbound.go 设计（见 docs/adr/0002）：
解析器发起的每个 HTTP 请求（含重定向后的每一跳）都必须落在该平台的
分享域名或上游域名内；直连时目标主机解析出的全部 IP 必须是公网地址；
跨主机跳转剥离敏感请求头。配置代理时不做本地 DNS 校验，由代理负责出口。
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from .parser.base import VideoSource

# 解析响应体大小上限（字节），对齐 Go 版 maxParseResponseBytes
MAX_RESPONSE_BYTES = 16 * 1024 * 1024

# 各平台除分享域名（parser/__init__.py 的 domain_list）外允许的上游主机：
# 平台 API、短链跳转目标与封面探测地址
UPSTREAM_DOMAINS: dict[VideoSource, list[str]] = {
    VideoSource.AcFun: ["acfun.cn", "tools.thatwind.com"],
    VideoSource.BiliBili: ["bilibili.com"],
    VideoSource.CCTV: ["vdn.apps.cntv.cn"],
    VideoSource.DouYin: [
        "douyin.com",
        "iesdouyin.com",
        "aweme.snssdk.com",
        "douyinvod.com",
    ],
    VideoSource.HuYa: ["huya.com"],
    VideoSource.KuaiShou: ["kuaishou.com", "chenzhongtech.com"],
    VideoSource.PiPiGaoXiao: ["ippzone.com"],
    VideoSource.PiPiXia: ["pipix.com"],
    VideoSource.QQVideo: ["vv.video.qq.com", "puui.qpic.cn"],
    VideoSource.QuanMin: ["quanmin.hao222.com"],
    VideoSource.RedBook: ["xiaohongshu.com"],
    VideoSource.Twitter: ["cdn.syndication.twimg.com"],
    VideoSource.WeiBo: ["m.weibo.cn"],
    VideoSource.WeiShi: ["h5.weishi.qq.com"],
    VideoSource.XiGua: ["m.ixigua.com"],
}


class OutboundError(Exception):
    """出站请求被边界拒绝（域名、协议或 IP 不在允许范围内）。"""


class ResponseTooLargeError(Exception):
    """上游响应体超过大小限制。"""


# 跨主机跳转时需要剥离的敏感请求头（httpx 不会自动生成 Referer，
# 因此只需处理解析器显式设置后被重定向复制的头）
SENSITIVE_REQUEST_HEADERS = (
    "authorization",
    "cookie",
    "proxy-authorization",
    "referer",
)

# Python ipaddress 未覆盖、需要显式排除的特殊用途网段（对齐 Go 版 specialAddresses）
SPECIAL_PURPOSE_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "192.31.196.0/24",  # AS112 任播
        "192.52.193.0/24",  # AMRP
        "192.88.99.0/24",  # 弃用的 6to4 中继任播
        "192.175.48.0/24",  # 6to4 中继任播
        "2001::/23",  # IETF 协议分配
        "2002::/16",  # 6to4
        "2620:4f:8000::/48",  # 直播 DNS64
        "3fff::/20",  # 文档示例
    )
)

_GLOBAL_IPV6 = ipaddress.ip_network("2000::/3")


def _unmap(ip: ipaddress.IPv4Address | ipaddress.IPv6Address):
    """IPv4-mapped IPv6 地址归一化为 IPv4。"""
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return mapped
    return ip


def public_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """地址是否为可公网路由的地址。"""
    ip = _unmap(ip)
    if any(ip in net for net in SPECIAL_PURPOSE_NETWORKS if net.version == ip.version):
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        return ip in _GLOBAL_IPV6 and ip.is_global
    return ip.is_global


def http_hostname(url: str | httpx.URL) -> str | None:
    """提取并校验 http(s) URL 的主机名，不合法时返回 None。

    只允许 http/https 协议、默认端口（80/443 或未写端口）、无 userinfo；
    主机名小写并去掉结尾的点号。
    """
    if isinstance(url, httpx.URL):
        scheme = url.scheme
        host = url.host
        try:
            port = url.port
        except httpx.InvalidURL:
            return None
        has_userinfo = bool(url.username or url.password)
    else:
        try:
            parts = urlsplit(url)
            port = parts.port  # 非法端口在此抛 ValueError
        except ValueError:
            return None
        scheme = parts.scheme
        host = parts.hostname
        has_userinfo = bool(parts.username or parts.password)

    if not host or has_userinfo:
        return None
    scheme = scheme.lower()
    if scheme not in ("http", "https"):
        return None
    if port is not None and port not in (80, 443):
        return None
    return host.rstrip(".").lower()


def host_matches(host: str, domain: str) -> bool:
    """host 是否等于 domain 或是它的子域名（DNS 标签边界）。"""
    return host == domain or host.endswith("." + domain)


def allowed_hosts(source: VideoSource) -> tuple[str, ...]:
    """平台允许的全部出站主机：分享域名 + 上游域名。"""
    # 延迟导入避免 parser/__init__ 与本模块的循环依赖
    from .parser import video_source_info_mapping

    hosts = list(video_source_info_mapping[source]["domain_list"])
    hosts.extend(UPSTREAM_DOMAINS.get(source, []))
    return tuple(dict.fromkeys(hosts))


async def resolve_public_host(host: str) -> None:
    """直连模式下要求 host 解析出的全部 IP 都是公网地址。"""
    # IP 字面量直接校验（域名白名单通常已经拒绝，这里是兜底）
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not public_address(literal):
            raise OutboundError("目标主机是 IP 字面量且非公网地址")
        return

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.run_in_executor(None, socket.getaddrinfo, host, None)
    except OSError as err:
        raise OutboundError(f"目标主机解析失败: {err.__class__.__name__}") from err
    addresses = {_unmap(ipaddress.ip_address(info[4][0])) for info in infos}
    if not addresses:
        raise OutboundError("目标主机未解析到任何地址")
    for ip in addresses:
        if not public_address(ip):
            raise OutboundError("目标主机解析到非公网地址")


class _CappedAsyncByteStream(httpx.AsyncByteStream):
    """限制响应体累计字节数的流包装。"""

    def __init__(self, inner: httpx.AsyncByteStream, limit: int):
        self._inner = inner
        self._limit = limit

    async def __aiter__(self):
        total = 0
        async for chunk in self._inner:
            total += len(chunk)
            if total > self._limit:
                raise ResponseTooLargeError("上游响应超出大小限制")
            yield chunk

    async def aclose(self) -> None:
        await self._inner.aclose()


class CheckedAsyncTransport(httpx.AsyncBaseTransport):
    """按平台域名白名单校验每一跳请求的 httpx transport。

    - 域名/协议/端口/userinfo 校验（含重定向后的每一跳）
    - 直连时校验 DNS 解析结果全部为公网 IP；配置代理时交由代理约束出口
    - 与首跳不同主机的请求剥离 Cookie/Authorization/Referer 等敏感头
    - 响应体限制在 max_response_bytes 内
    """

    def __init__(
        self,
        source: VideoSource,
        proxy: str | None = None,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ):
        self._allowed = allowed_hosts(source)
        self._proxy = proxy
        self._max_response_bytes = max_response_bytes
        self._anchor: tuple[str, str] | None = None
        # trust_env=False：不读取环境变量代理，代理只认 PARSE_VIDEO_PROXY
        self._inner = httpx.AsyncHTTPTransport(proxy=proxy, trust_env=False)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        host = http_hostname(url)
        if host is None or not any(host_matches(host, d) for d in self._allowed):
            raise OutboundError(f"目标主机不在平台允许范围内: {host or url.scheme}")

        anchor = (url.scheme, (url.host or "").lower())
        if self._anchor is None:
            self._anchor = anchor
        elif anchor != self._anchor:
            for name in SENSITIVE_REQUEST_HEADERS:
                if name in request.headers:
                    del request.headers[name]

        if self._proxy is None:
            await resolve_public_host(host)

        response = await self._inner.handle_async_request(request)

        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_response_bytes:
                    await response.aclose()
                    raise ResponseTooLargeError("上游响应超出大小限制")
            except ValueError:
                pass  # 非法 content-length 交给流式计数兜底
        response.stream = _CappedAsyncByteStream(
            response.stream, self._max_response_bytes
        )
        return response

    async def aclose(self) -> None:
        await self._inner.aclose()

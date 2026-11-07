import os
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx

from .outbound import CheckedAsyncTransport
from .parser.base import VideoSource

URL_REG = re.compile(r"http[s]?:\/\/[\w.-]+[\w\/-]*[\w.-]*\??[\w=&:\-\+\%.]*[/]*")

# 解析请求默认超时与重定向上限（对齐 Go 版 parseTimeout / maxRedirects）
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_MAX_REDIRECTS = 10


def extract_url(text: str) -> str | None:
    """从文本中提取第一个匹配的 URL"""
    match = URL_REG.search(text)
    return match.group() if match else None


def get_val_from_url_by_query_key(url: str, query_key: str) -> str:
    """
    从url的query参数中解析出query_key对应的值
    :param url: url地址
    :param query_key: query参数的key
    :return:
    """
    url_res = urlparse(url)
    url_query = parse_qs(url_res.query, keep_blank_values=True)

    try:
        query_val = url_query[query_key][0]
    except KeyError:
        raise KeyError(f"url中不存在query参数: {query_key}")

    if len(query_val) == 0:
        raise ValueError(f"url中query参数值长度为0: {query_key}")

    return url_query[query_key][0]


def create_async_client(
    source: Optional[VideoSource] = None, **kwargs
) -> httpx.AsyncClient:
    """创建 httpx.AsyncClient，自动注入代理、超时与出站边界配置。

    - 从环境变量 PARSE_VIDEO_PROXY 读取代理地址（如 http://user:pass@host:port），
      未设置则不使用代理；代理故障直接抛错，不回退直连。
      trust_env=False：不读取 HTTP(S)_PROXY/ALL_PROXY 等环境变量代理，
      出口代理只认 PARSE_VIDEO_PROXY（见 docs/adr/0001、0002）
    - 传入 source 时挂载 CheckedAsyncTransport：每一跳请求（含重定向）
      限定在该平台的域名白名单内，直连时校验解析 IP 为公网地址，
      响应体限制在 outbound.MAX_RESPONSE_BYTES 内
    - 默认 30s 总超时 / 10s 连接超时，重定向最多 10 跳；显式传参可覆盖
    其余参数透传给 httpx.AsyncClient。
    """
    proxy = os.getenv("PARSE_VIDEO_PROXY")
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    kwargs.setdefault("max_redirects", DEFAULT_MAX_REDIRECTS)
    kwargs.setdefault("trust_env", False)
    if source is not None:
        # 自定义 transport 内部已处理代理，不能在 client 上重复传 proxy
        kwargs["transport"] = CheckedAsyncTransport(source=source, proxy=proxy)
    elif proxy:
        kwargs["proxy"] = proxy
    return httpx.AsyncClient(**kwargs)

import os
import re
from urllib.parse import parse_qs, urlparse

import httpx

URL_REG = re.compile(r"http[s]?:\/\/[\w.-]+[\w\/-]*[\w.-]*\??[\w=&:\-\+\%.]*[/]*")


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


def create_async_client(**kwargs) -> httpx.AsyncClient:
    """创建 httpx.AsyncClient，自动注入代理配置。

    从环境变量 PARSE_VIDEO_PROXY 读取代理地址（如 http://user:pass@host:port），
    未设置则不使用代理。其余参数透传给 httpx.AsyncClient。
    """
    proxy = os.getenv("PARSE_VIDEO_PROXY")
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.AsyncClient(**kwargs)

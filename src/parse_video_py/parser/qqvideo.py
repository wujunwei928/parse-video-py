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
            "https://vv.video.qq.com/getinfo"
            f"?vids={video_id}"
            "&platform=101001&otype=json&defn=shd"
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
                f'腾讯视频API返回错误: {data.get("msg", "")}' f' (em: {data.get("em")})'
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
        cover_url = f"https://puui.qpic.cn/vpic_cover" f"/{vid}/{vid}_hz.jpg/496"

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

        # PC端页面
        if "v.qq.com" in host:
            return self._extract_vid_from_path(parsed.path)

        raise ValueError(f"不支持的腾讯视频域名: {host}")

    def _extract_vid_from_path(self, path: str) -> str:
        """从 URL 路径中提取视频 ID"""
        match = _qq_vid_path_re.search(path)
        if match and match.group(1):
            return match.group(1)
        raise ValueError(f"无法从路径 {path} 中提取视频ID")

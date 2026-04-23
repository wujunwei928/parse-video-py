import re

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo

# 匹配央视网页面中嵌入的视频 GUID
_cctv_guid_re = re.compile(r'var\s+guid\s*=\s*"([^"]+)"')


class CCTV(BaseParser):
    """
    央视网
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        # 请求页面 HTML 提取视频 GUID
        guid = await self._extract_guid(share_url)
        return await self.parse_video_id(guid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        if not video_id:
            raise ValueError("视频GUID不能为空")

        api_url = "https://vdn.apps.cntv.cn/api/" f"getHttpVideoInfo.do?pid={video_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=self.get_default_headers())
            response.raise_for_status()

        data = response.json()

        # 检查 API 状态
        status = data.get("status", "")
        if status != "001":
            raise Exception(
                f"央视网视频API返回错误 (status: {status}, " f'title: {data.get("title", "")})'
            )

        # 提取 HLS 视频播放地址
        # 注：manifest 中的 h5e/enc/enc2 高码率流在
        # H.264 帧级加扰，播放花屏，仅 hls_url 可正常播放
        video_url = data.get("hls_url", "")
        if not video_url:
            raise Exception("未找到视频播放地址")

        # 提取视频元信息
        title = data.get("title", "")
        cover_url = data.get("image", "")
        play_channel = data.get("play_channel", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(name=play_channel),
        )

    async def _extract_guid(self, page_url: str) -> str:
        """从页面 URL 请求并提取视频 GUID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(page_url, headers=self.get_default_headers())
            response.raise_for_status()

        return self._extract_guid_from_html(response.text)

    @staticmethod
    def _extract_guid_from_html(html: str) -> str:
        """从 HTML 字符串中提取视频 GUID"""
        match = _cctv_guid_re.search(html)
        if match and match.group(1):
            return match.group(1)
        raise ValueError("页面中未找到视频GUID")

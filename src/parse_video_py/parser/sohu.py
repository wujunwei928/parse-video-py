import base64
import re

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo

# 匹配 tv.sohu.com/v/{base64}.html 格式的路径
_sohu_base64_vid_re = re.compile(r"/v/([A-Za-z0-9+/=]+)\.html")

# 匹配 us/{uid}/{vid}.shtml 格式的路径
_sohu_user_vid_re = re.compile(r"/?us/\d+/(\d+)\.shtml")


class Sohu(BaseParser):
    """
    搜狐视频
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        vid = self._extract_vid(share_url)
        return await self.parse_video_id(vid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        if not video_id:
            raise ValueError("视频ID不能为空")

        api_url = (
            f"https://api.tv.sohu.com/v4/video/info/"
            f"{video_id}.json"
            "?site=2"
            "&api_key=9854b2afa779e1a6bcdd07b217417549"
            "&sver=6.2.0"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=self.get_default_headers())
            response.raise_for_status()

        data = response.json()

        # 检查API状态
        if data.get("status") != 200:
            raise Exception(
                f"搜狐视频API返回错误: "
                f'{data.get("statusText", "")} '
                f'(status: {data.get("status")})'
            )

        video_data = data.get("data")
        if not video_data:
            raise Exception("API响应中未找到视频数据")

        # 提取视频播放地址，优先高清，回退到下载地址
        video_url = video_data.get("url_high_mp4", "") or (
            video_data.get("download_url", "")
        )
        if not video_url:
            raise Exception("未找到视频播放地址")

        # 提取视频元信息
        title = video_data.get("video_name", "")
        cover_url = video_data.get("originalCutCover", "")

        # 提取作者信息
        user_info = video_data.get("user", {})
        author = VideoAuthor(
            uid=str(user_info.get("user_id", "")),
            name=user_info.get("nickname", ""),
            avatar=user_info.get("small_pic", ""),
        )

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=author,
        )

    def _extract_vid(self, raw_url: str) -> str:
        """从 URL 中提取搜狐视频 ID"""
        # 匹配 tv.sohu.com/v/{base64}.html 格式
        match = _sohu_base64_vid_re.search(raw_url)
        if match:
            decoded = base64.b64decode(match.group(1)).decode("utf-8")
            return self._extract_vid_from_path(decoded)

        # 匹配 my.tv.sohu.com/us/{uid}/{vid}.shtml 格式
        if "my.tv.sohu.com" in raw_url or "tv.sohu.com/us/" in raw_url:
            return self._extract_vid_from_path(raw_url)

        raise ValueError("不是有效的搜狐视频链接")

    def _extract_vid_from_path(self, path: str) -> str:
        """从路径中提取视频 ID"""
        match = _sohu_user_vid_re.search(path)
        if match and match.group(1):
            return match.group(1)
        raise ValueError(f"无法从路径 {path} 中提取视频ID")

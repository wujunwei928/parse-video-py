import time
from urllib.parse import urlparse

import fake_useragent
import httpx

from .base import BaseParser, VideoInfo


class LiShiPin(BaseParser):
    """
    梨视频
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        url_res = urlparse(share_url)

        video_id = url_res.path.replace("/detail_", "")
        if len(video_id) == 0:
            raise ValueError("parse video_id from share url fail")

        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        now = int(time.time())
        req_url = (
            f"https://www.pearvideo.com/videoStatus.jsp?contId={video_id}&mrd={now}"
        )

        async with httpx.AsyncClient() as client:
            headers = {
                "Referer": f"https://www.pearvideo.com/detail_{video_id}",
                "User-Agent": fake_useragent.UserAgent(os=["windows"]).random,
            }
            response = await client.get(req_url, headers=headers)

        if response.status_code != 200:
            raise Exception("failed to fetch data")

        json_data = response.json()

        # 获取 videoInfo 字段的值
        video_src_url = json_data["videoInfo"]["videos"]["srcUrl"]
        timer = json_data["systemTime"]
        video_url = video_src_url.replace(timer, f"cont-{video_id}")
        cover_url = json_data["videoInfo"]["video_image"]

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
        )

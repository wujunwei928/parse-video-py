import re

import fake_useragent
import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class HuYa(BaseParser):
    """
    虎牙
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        re_pattern = r"\/(\d+).html"
        re_result = re.search(re_pattern, share_url)

        if not re_result:
            raise Exception("parse video_id from share url fail")

        video_id = re_result.group(1)
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://liveapi.huya.com/moment/getMomentContent?videoId={video_id}"
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": fake_useragent.UserAgent(os=["windows"]).random,
                "Referer": "https://v.huya.com/",
            }
            response = await client.get(req_url, headers=headers)
            response.raise_for_status()

        json_data = response.json()
        data = json_data["data"]["moment"]["videoInfo"]
        if data["uid"] == 0:
            raise Exception("video not found")

        video_info = VideoInfo(
            video_url=data["definitions"][0]["url"],
            cover_url=data["videoCover"],
            title=data["videoTitle"],
            author=VideoAuthor(
                uid=str(data["uid"]),
                name=data["actorNick"],
                avatar=data["actorAvatarUrl"],
            ),
        )
        return video_info

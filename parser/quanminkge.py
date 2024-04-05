import json
import re

import fake_useragent
import httpx

from utils import get_val_from_url_by_query_key

from .base import BaseParser, VideoAuthor, VideoInfo


class QuanMinKGe(BaseParser):
    """
    全民K歌
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = get_val_from_url_by_query_key(share_url, "s")
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://kg.qq.com/node/play?s={video_id}"
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": fake_useragent.UserAgent(os="windows").random,
            }
            response = await client.get(req_url, headers=headers)
            response.raise_for_status()

        re_pattern = r"window.__DATA__ = (.*?); </script>"
        re_result = re.search(re_pattern, response.text)

        if not re_result or len(re_result.groups()) < 1:
            raise Exception("failed to parse video JSON info from HTML")

        json_text = re_result.group(1).strip()
        json_data = json.loads(json_text)
        data = json_data["detail"]

        video_info = VideoInfo(
            video_url=data["playurl_video"],
            cover_url=data["cover"],
            title=data["content"],
            author=VideoAuthor(
                uid=data["uid"],
                name=data["nick"],
                avatar=data["avatar"],
            ),
        )
        return video_info

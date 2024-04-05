import json
import re

import fake_useragent
import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class KuaiShou(BaseParser):
    """
    快手
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["windows"]).random,
            "Referer": "https://v.kuaishou.com/",
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(share_url, headers=headers)

        re_pattern = r"window.__APOLLO_STATE__=(.*?);\(function"
        re_result = re.search(re_pattern, response.text)

        if not re_result or len(re_result.groups()) < 1:
            raise Exception("failed to parse video JSON info from HTML")

        json_text = re_result.group(1).strip()
        json_data = json.loads(json_text)
        video_info = None
        author_info = None
        for json_key, json_val in json_data["defaultClient"].items():
            if json_key.startswith("VisionVideoDetailAuthor"):
                author_info = json_val
            elif json_key.startswith("VisionVideoDetailPhoto"):
                video_info = json_val

        if not video_info or not author_info:
            raise Exception("failed to parse video JSON info from HTML")

        video_info = VideoInfo(
            video_url=video_info["photoUrl"],
            cover_url=video_info["coverUrl"],
            title=video_info["caption"],
            author=VideoAuthor(
                uid=author_info["id"],
                name=author_info["name"],
                avatar=author_info["headerUrl"],
            ),
        )
        return video_info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("快手暂不支持直接解析视频ID")

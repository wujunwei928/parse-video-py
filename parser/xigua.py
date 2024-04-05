import json
from urllib.parse import unquote

import fake_useragent
import httpx
from parsel import Selector

from .base import BaseParser, VideoAuthor, VideoInfo


class XiGua(BaseParser):
    """
    西瓜视频
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["android"]).random,
        }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(share_url, headers=headers)

        location_url = response.headers.get("location", "")
        video_id = location_url.split("?")[0].strip("/").split("/")[-1]
        if len(video_id) <= 0:
            raise Exception("failed to get video_id from share URL")

        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        # 注意： url中的 video_id 后面不要有 /， 否则返回格式不一样
        req_url = (
            f"https://m.ixigua.com/douyin/share/video/{video_id}"
            f"?aweme_type=107&schema_type=1&utm_source=copy"
            f"&utm_campaign=client_share&utm_medium=android&app=aweme"
        )

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(req_url, headers=self.get_default_headers())
            response.raise_for_status()

        sel = Selector(response.text)
        render_data = sel.css("script#RENDER_DATA::text").get(default="")
        if len(render_data) <= 0:
            raise Exception("failed to parse render data from HTML")
        render_data = unquote(render_data)  # urldecode

        json_data = json.loads(render_data)
        data = json_data["app"]["videoInfoRes"]["item_list"][0]
        video_url = data["video"]["play_addr"]["url_list"][0].replace("playwm", "play")

        video_info = VideoInfo(
            video_url=video_url,
            cover_url=data["video"]["cover"]["url_list"][0],
            title=data["desc"],
            author=VideoAuthor(
                uid=data["author"]["unique_id"],
                name=data["author"]["nickname"],
                avatar=data["author"]["avatar_thumb"]["url_list"][0],
            ),
        )
        return video_info

import json
from urllib.parse import unquote

import httpx
from parsel import Selector

from .base import BaseParser, VideoAuthor, VideoInfo


class DouYin(BaseParser):
    """
    抖音 / 抖音火山版
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(share_url, headers=self.get_default_headers())
            response.raise_for_status()

        sel = Selector(response.text)
        render_data = sel.css("script#RENDER_DATA::text").get(default="")
        if len(render_data) <= 0:
            raise Exception("failed to parse render data from HTML")
        render_data = unquote(render_data)  # urldecode

        json_data = json.loads(render_data)
        data = json_data["app"]["videoInfoRes"]["item_list"][0]
        video_url = data["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
        # 获取重定向后的mp4视频地址
        video_mp4_url = await self.get_video_redirect_url(video_url)

        video_info = VideoInfo(
            video_url=video_mp4_url,
            cover_url=data["video"]["cover"]["url_list"][0],
            title=data["desc"],
            author=VideoAuthor(
                uid=data["author"]["unique_id"],
                name=data["author"]["nickname"],
                avatar=data["author"]["avatar_thumb"]["url_list"][0],
            ),
        )
        return video_info

    async def get_video_redirect_url(self, video_url: str) -> str:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(video_url, headers=self.get_default_headers())
        return response.headers.get("location", "")

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
        return await self.parse_share_url(req_url)

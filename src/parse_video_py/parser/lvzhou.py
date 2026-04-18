import re

import httpx
from parsel import Selector

from .base import BaseParser, VideoAuthor, VideoInfo


class LvZhou(BaseParser):
    """
    绿洲
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(share_url, headers=self.get_default_headers())
            response.raise_for_status()

        sel = Selector(response.text)

        video_url = sel.css("video::attr(src)").get()
        author_avatar = sel.css("a.avatar img::attr(src)").get()
        video_cover_style = sel.css("div.video-cover::attr(style)").get(default="")

        cover_url = ""
        if video_cover_style:
            match = re.search(r"background-image:url\((.*)\)", video_cover_style)
            if match:
                cover_url = match.group(1)

        title = sel.css("div.status-title::text").get()
        author_name = sel.css("div.nickname::text").get()

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(
                name=author_name,
                avatar=author_avatar,
            ),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        share_url = f"https://m.oasis.weibo.cn/v1/h5/share?sid={video_id}"
        return await self.parse_share_url(share_url)

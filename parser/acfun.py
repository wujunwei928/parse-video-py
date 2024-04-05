import json
import re

import httpx
from parsel import Selector

from .base import BaseParser, VideoAuthor, VideoInfo


class AcFun(BaseParser):
    """
    A站：视频地址是m3u8, 可以使用网站 https://tools.thatwind.com/tool/m3u8downloader 下载
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(share_url, headers=self.get_default_headers())
            response.raise_for_status()

        re_video_pattern = r"var videoInfo =\s(.*?);"
        re_video_result = re.search(re_video_pattern, response.text)
        if not re_video_result or len(re_video_result.groups()) < 1:
            raise Exception("failed to parse video JSON info from HTML")

        video_text = re_video_result.group(1).strip()
        video_data = json.loads(video_text)

        # 解析视频播放地址
        re_play_info_pattern = r"var playInfo =\s(.*?);"
        re_play_info_result = re.search(re_play_info_pattern, response.text)
        if not re_play_info_result or len(re_play_info_result.groups()) < 1:
            raise Exception("failed to parse play info JSON info from HTML")

        play_info_text = re_play_info_result.group(1).strip()
        play_info_data = json.loads(play_info_text)

        # 解析用户信息
        sel = Selector(response.text)
        uid = (
            sel.css("div.up-info > a.info-item1::attr(href)")
            .get(default="")
            .replace("/upPage/", "")
        )
        name = sel.css("div.up-info span.up-name::text").get(default="")
        avatar = sel.css("div.up-info span.up-avatar > img::attr(src)").get(default="")

        video_info = VideoInfo(
            video_url=play_info_data["streams"][0]["playUrls"][0],
            cover_url=video_data["cover"],
            title=video_data["title"],
            author=VideoAuthor(
                uid=uid,
                name=name,
                avatar=avatar,
            ),
        )
        return video_info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        # acid, 格式: ac36935385
        req_url = f"https://www.acfun.cn/v/{video_id}"
        return await self.parse_share_url(req_url)

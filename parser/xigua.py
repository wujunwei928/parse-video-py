import json
import re

import fake_useragent
import httpx

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

        pattern = re.compile(
            pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
            flags=re.DOTALL,
        )
        find_res = pattern.search(response.text)

        if not find_res or not find_res.group(1):
            raise ValueError("parse video json info from html fail")

        json_data = json.loads(find_res.group(1).strip())
        original_video_info = json_data["loaderData"]["video_(id)/page"]["videoInfoRes"]

        # 如果没有视频信息，获取并抛出异常
        if len(original_video_info["item_list"]) == 0:
            err_detail_msg = "failed to parse video info from HTML"
            if len(filter_list := original_video_info["filter_list"]) > 0:
                err_detail_msg = filter_list[0]["detail_msg"]
            raise Exception(err_detail_msg)

        data = original_video_info["item_list"][0]
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

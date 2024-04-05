import json

import fake_useragent
import httpx
from parsel import Selector

from .base import BaseParser, VideoAuthor, VideoInfo


class XinPianChang(BaseParser):
    """
    新片场
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["windows"]).random,
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.xinpianchang.com/",
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(share_url, headers=headers)
            response.raise_for_status()

        sel = Selector(response.text)
        json_text = sel.css("script#__NEXT_DATA__::text").get()
        json_data = json.loads(json_text)
        data = json_data["props"]["pageProps"]["detail"]

        # 获取 appKey 和 media_id， 另外调用接口获取mp4视频地址
        app_key = data["video"]["appKey"]
        media_id = data["media_id"]
        req_mp4_url = (
            f"https://mod-api.xinpianchang.com/mod/api/v2/media/{media_id}"
            f"?appKey={app_key}&extend=userInfo%2CuserStatus"
        )
        async with httpx.AsyncClient(follow_redirects=True) as client:
            mp4_response = await client.get(req_mp4_url, headers=headers)
            mp4_response.raise_for_status()
        mp4_data = mp4_response.json()
        video_url = mp4_data["data"]["resource"]["progressive"][0]["url"]

        video_info = VideoInfo(
            video_url=video_url,
            cover_url=data["cover"],
            title=data["title"],
            author=VideoAuthor(
                uid=str(data["author"]["userinfo"]["id"]),
                name=data["author"]["userinfo"]["username"],
                avatar=data["author"]["userinfo"]["avatar"],
            ),
        )

        return video_info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("新片场暂不支持直接解析视频ID")

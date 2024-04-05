import fake_useragent
import httpx

from utils import get_val_from_url_by_query_key

from .base import BaseParser, VideoAuthor, VideoInfo


class SixRoom(BaseParser):
    """
    六间房
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        if "watchMini.php?vid=" in share_url:
            video_id = get_val_from_url_by_query_key(share_url, "vid")
        else:
            video_id = share_url.split("?")[0].strip("/").split("/")[-1]

        if len(video_id) == 0:
            raise Exception("parse video id from share url failed")

        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = (
            f"https://v.6.cn/coop/mobile/index.php?"
            f"padapi=minivideo-watchVideo.php&av=3.0"
            f"&encpass=&logiuid=&isnew=1&from=0&vid={video_id}"
        )
        headers = {
            "Referer": f"https://m.6.cn/v/{video_id}",
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
        }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(req_url, headers=headers)
            response.raise_for_status()

        json_data = response.json()
        data = json_data["content"]

        video_info = VideoInfo(
            video_url=data["playurl"],
            cover_url=data["picurl"],
            title=data["title"],
            author=VideoAuthor(
                uid="",
                name=data["alias"],
                avatar=data["picuser"],
            ),
        )
        return video_info

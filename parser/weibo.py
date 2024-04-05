import fake_useragent
import httpx

from utils import get_val_from_url_by_query_key

from .base import BaseParser, VideoAuthor, VideoInfo


class WeiBo(BaseParser):
    """
    微博
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        if "show?fid=" in share_url:
            video_id = get_val_from_url_by_query_key(share_url, "fid")
        else:
            video_id = share_url.split("?")[0].strip("/").split("/")[-1]

        if len(video_id) == 0:
            raise Exception("parse video id from share url failed")

        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://h5.video.weibo.com/api/component?page=/show/{video_id}"
        headers = {
            "Referer": f"https://h5.video.weibo.com/show/{video_id}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
        }
        post_content = 'data={"Component_Play_Playinfo":{"oid":"' + video_id + '"}}'
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(req_url, headers=headers, content=post_content)
            response.raise_for_status()

        json_data = response.json()
        data = json_data["data"]["Component_Play_Playinfo"]

        video_url = data["stream_url"]
        if len(data["urls"]) > 0:
            # stream_url码率最低，urls中第一条码率最高
            _, first_mp4_url = next(iter(data["urls"].items()))
            video_url = f"https:{first_mp4_url}"

        video_info = VideoInfo(
            video_url=video_url,
            cover_url="https:" + data["cover_image"],
            title=data["title"],
            author=VideoAuthor(
                uid=str(data["user"]["id"]),
                name=data["author"],
                avatar="https:" + data["avatar"],
            ),
        )
        return video_info

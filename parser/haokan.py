import httpx

from utils import get_val_from_url_by_query_key

from .base import BaseParser, VideoAuthor, VideoInfo


class HaoKan(BaseParser):
    """
    好看视频
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = get_val_from_url_by_query_key(share_url, "vid")
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://haokan.baidu.com/v?_format=json&vid={video_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(req_url, headers=self.get_default_headers())
            response.raise_for_status()

        json_data = response.json()
        # 接口返回错误
        if json_data["errno"] != 0:
            raise Exception(json_data["error"])

        video_data = json_data["data"]["apiData"]["curVideoMeta"]
        user_data = video_data["mth"]

        video_info = VideoInfo(
            video_url=video_data["playurl"],
            cover_url=video_data["poster"],
            title=video_data["title"],
            author=VideoAuthor(
                uid=user_data["mthid"],
                name=user_data["author_name"],
                avatar=user_data["author_photo"],
            ),
        )
        return video_info

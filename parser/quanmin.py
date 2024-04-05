import httpx

from utils import get_val_from_url_by_query_key

from .base import BaseParser, VideoAuthor, VideoInfo


class QuanMin(BaseParser):
    """
    度小视(原 全民小视频)
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = get_val_from_url_by_query_key(share_url, "vid")
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = (
            "https://quanmin.hao222.com/wise/growth/api/sv/immerse"
            f"?source=share-h5&pd=qm_share_mvideo&_format=json&vid={video_id}"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(req_url, headers=self.get_default_headers())
            response.raise_for_status()

        json_data = response.json()
        data = json_data["data"]
        # 接口返回错误
        if json_data["errno"] != 0:
            raise Exception(json_data["error"])
        # 视频状态错误
        if len(data["meta"]["statusText"]) > 0:
            raise Exception(data["meta"]["statusText"])

        # 获取视频标题，如果没有则使用分享标题
        video_title = data["meta"]["title"]
        if len(video_title) == 0:
            video_title = data["shareInfo"]["title"]

        video_info = VideoInfo(
            video_url=data["meta"]["video_info"]["clarityUrl"][1]["url"],
            cover_url=data["meta"]["image"],
            title=video_title,
            author=VideoAuthor(
                uid=data["author"]["id"],
                name=data["author"]["name"],
                avatar=data["author"]["icon"],
            ),
        )
        return video_info

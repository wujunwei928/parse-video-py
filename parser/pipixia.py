import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class PiPiXia(BaseParser):
    """
    皮皮虾
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(share_url, headers=self.get_default_headers())
        location_url = response.headers.get("location", "")
        if len(location_url) <= 0:
            raise Exception("failed to get location url from share url")

        video_id = location_url.split("?")[0].split("/")[-1]

        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = (
            f"https://is.snssdk.com/bds/cell/detail/"
            f"?cell_type=1&aid=1319&app_name=super&cell_id={video_id}"
        )
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(req_url, headers=self.get_default_headers())
            response.raise_for_status()

        json_data = response.json()
        data = json_data["data"]["data"]["item"]
        video_info = VideoInfo(
            video_url=data["origin_video_download"]["url_list"][0]["url"],
            cover_url=data["cover"]["url_list"][0]["url"],
            title=data["share"]["title"],
            author=VideoAuthor(
                uid=str(data["author"]["id"]),
                name=data["author"]["name"],
                avatar=data["author"]["avatar"]["download_list"][0]["url"],
            ),
        )

        return video_info

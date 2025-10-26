import re
from urllib.parse import urlparse

import fake_useragent
import httpx

from utils import get_val_from_url_by_query_key

from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class WeiBo(BaseParser):
    """
    微博
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        # Handle video URLs
        if "show?fid=" in share_url:
            video_id = get_val_from_url_by_query_key(share_url, "fid")
            return await self.parse_video_id(video_id)
        elif "/tv/show/" in share_url:
            url_info = urlparse(share_url)
            video_id = url_info.path.replace("/tv/show/", "")
            return await self.parse_video_id(video_id)
        else:
            # Handle regular post URLs (potential image albums)
            # Extract post ID from URLs like https://weibo.com/2543858012/Q9pcJ4S21
            url_info = urlparse(share_url)
            path_parts = url_info.path.strip("/").split("/")
            if len(path_parts) >= 2:
                post_id = path_parts[-1]
                return await self.parse_post_url(post_id, share_url)

        raise Exception("unsupported weibo url format")

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

    async def parse_post_url(self, post_id: str, original_url: str) -> VideoInfo:
        """
        Parse Weibo post (potential image album)
        """
        # Try mobile API first
        req_url = f"https://m.weibo.cn/statuses/show?id={post_id}"
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
            "Referer": "https://m.weibo.cn/",
            "Content-Type": "application/json;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(req_url, headers=headers)
                response.raise_for_status()

            json_data = response.json()
            if "data" in json_data:
                return await self._parse_mobile_api_data(json_data["data"])
        except Exception:
            pass

        # Fallback to desktop page parsing using the original URL
        headers = {
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(original_url, headers=headers)
            response.raise_for_status()

        return await self._parse_html_page(response.text)

    async def _parse_mobile_api_data(self, data: dict) -> VideoInfo:
        """
        Parse data from mobile API
        """
        # Extract basic info
        title = data.get("text", "")
        author_info = data.get("user", {})
        author_name = author_info.get("screen_name", "")
        author_avatar = author_info.get("avatar_large", "")

        # Get images
        images = []
        pics_data = data.get("pics", [])
        for pic in pics_data:
            # Get the largest image URL available
            large_pic_url = ""
            for size in ["large", "original", "bmiddle", "url"]:
                if size in pic and pic[size].get("url"):
                    large_pic_url = pic[size]["url"]
                    break

            if large_pic_url:
                images.append(ImgInfo(url=large_pic_url))

        video_info = VideoInfo(
            video_url="",  # Regular posts don't have videos
            cover_url="",
            title=self._clean_text(title),
            images=images,
            author=VideoAuthor(
                name=author_name,
                avatar=author_avatar,
            ),
        )
        return video_info

    async def _parse_html_page(self, html_content: str) -> VideoInfo:
        """
        Parse data from HTML page
        """
        # Try to extract data from $render_data script
        pattern = r"\$render_data\s*=\s*(.*?)\[0\]"
        match = re.search(pattern, html_content)
        if not match:
            raise Exception("parse weibo html page fail")

        json_str = match.group(1) + "[0]"
        import json

        data = json.loads(json_str)

        # Extract basic info
        status_data = data.get("status", {})
        title = status_data.get("text", "")
        author_info = status_data.get("user", {})
        author_name = author_info.get("screen_name", "")
        author_avatar = author_info.get("avatar_large", "")

        # Get images
        images = []
        pics_data = status_data.get("pics", [])
        for pic in pics_data:
            # Get the largest image URL available
            large_pic_url = ""
            for size in ["large", "original", "bmiddle", "url"]:
                if size in pic and pic[size].get("url"):
                    large_pic_url = pic[size]["url"]
                    break

            if large_pic_url:
                images.append(ImgInfo(url=large_pic_url))

        video_info = VideoInfo(
            video_url="",  # Regular posts don't have videos
            cover_url="",
            title=self._clean_text(title),
            images=images,
            author=VideoAuthor(
                name=author_name,
                avatar=author_avatar,
            ),
        )
        return video_info

    def _clean_text(self, text: str) -> str:
        """
        Remove HTML tags from text
        """
        # Remove HTML tags
        cleaned = re.sub(r"<[^>]*>", "", text)
        return cleaned.strip()

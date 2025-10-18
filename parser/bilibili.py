import json
from urllib.parse import urlparse

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class BiliBili(BaseParser):
    """
    哔哩哔哩
    """

    # 添加Cookie可以爬取更高清的视频，记得要把下面请求里的Cookie的注释也去掉
    # BILI_COOKIE = "_uuid=; buvid_fp=; buvid4=; SESSDATA=; bili_jct=; DedeUserID=;"

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    )

    def get_default_headers(self) -> dict:
        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": "https://www.bilibili.com/",
        }
        # 如需爬取更高清的视频请取消这里的注释
        # headers["Cookie"] = self.BILI_COOKIE
        return headers

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        bvid = await self._get_bvid_from_url(share_url)
        return await self.parse_video_id(bvid)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        # 第一步：获取视频信息
        view_api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={video_id}"
        view_resp_data = await self._send_bili_request(view_api_url)

        view_resp = json.loads(view_resp_data)
        if view_resp.get("code") != 0 or not view_resp.get("data", {}).get("pages"):
            raise ValueError(f"无法获取该视频: {view_resp.get('message', '未知错误')}")

        data = view_resp["data"]
        first_page_cid = data["pages"][0]["cid"]

        # 第二步：获取播放链接
        play_api_url = (
            f"https://api.bilibili.com/x/player/playurl?"
            f"otype=json&fnver=0&fnval=0&qn=80&bvid={video_id}"
            f"&cid={first_page_cid}&platform=html5"
        )
        play_resp_data = await self._send_bili_request(play_api_url)

        play_resp = json.loads(play_resp_data)
        if play_resp.get("code") != 0:
            raise ValueError(
                f"B站API返回错误: {play_resp.get('message', '未知错误')} "
                f"(code: {play_resp.get('code')})"
            )

        # 提取视频URL
        video_url = ""
        play_data = play_resp.get("data", {})
        if play_data.get("durl") and len(play_data["durl"]) > 0:
            video_url = play_data["durl"][0].get("url", "")

        if not video_url:
            raise ValueError("无法获取该视频播放链接")

        # 构建视频信息
        video_info = VideoInfo(
            title=data.get("title", ""),
            video_url=video_url,
            cover_url=data.get("pic", ""),
            images=[],  # 空的图片列表
        )

        # 设置作者信息
        owner = data.get("owner", {})
        video_info.author = VideoAuthor(
            uid=str(owner.get("mid", "")),
            name=owner.get("name", ""),
            avatar=owner.get("face", ""),
        )

        return video_info

    async def _get_bvid_from_url(self, raw_url: str) -> str:
        """从URL中提取BVID"""
        try:
            parsed_url = urlparse(raw_url)
        except Exception:
            raise ValueError("URL格式无效")

        if "b23.tv" in parsed_url.netloc:
            # 处理短链接
            async with httpx.AsyncClient(follow_redirects=False) as client:
                resp = await client.get(raw_url, headers=self.get_default_headers())
                location = resp.headers.get("location")
                if not location:
                    raise ValueError("无法从b23.tv获取重定向链接")
                return await self._get_bvid_from_url(location)

        if "bilibili.com" in parsed_url.netloc:
            path = parsed_url.path.strip("/")
            parts = path.split("/")
            if len(parts) >= 2 and parts[0] == "video":
                if parts[1].startswith("BV"):
                    return parts[1]

        raise ValueError("不是有效的B站视频链接")

    async def _send_bili_request(self, api_url: str) -> str:
        """发送B站API请求"""
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=self.get_default_headers())
            if response.status_code != 200:
                raise ValueError(f"HTTP请求失败, 状态码: {response.status_code}")
            return response.text

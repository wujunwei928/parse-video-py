import json
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class YouTube(BaseParser):
    """
    YouTube 解析器
    参考 yt-dlp / youtube-dl 的页面 JSON 提取思路实现
    """

    WATCH_URL = "https://www.youtube.com/watch?v={video_id}&bpctr=9999999999&has_verified=1"

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = self._extract_video_id(share_url)
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        player_response = await self._fetch_player_response(video_id)

        video_details = player_response.get("videoDetails", {})
        streaming_data = player_response.get("streamingData", {})
        formats = (streaming_data.get("formats") or []) + (
            streaming_data.get("adaptiveFormats") or []
        )

        video_url = self._pick_best_video_url(formats)
        if not video_url:
            raise ValueError("无法获取 YouTube 视频直链")

        cover_url = self._pick_cover_url(video_details)

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=video_details.get("title", ""),
            author=VideoAuthor(
                uid=video_details.get("channelId", ""),
                name=video_details.get("author", ""),
                avatar="",
            ),
        )

    async def _fetch_player_response(self, video_id: str) -> dict:
        url = self.WATCH_URL.format(video_id=video_id)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        player_response = self._extract_player_response(resp.text)

        playability_status = player_response.get("playabilityStatus", {})
        status = playability_status.get("status", "")
        if status and status != "OK":
            reason = playability_status.get("reason", "")
            raise ValueError(f"YouTube 视频不可播放: {status} {reason}".strip())

        return player_response

    def _extract_player_response(self, html: str) -> dict:
        patterns = [
            r"ytInitialPlayerResponse\s*=\s*(\{.+?\});",
            r"ytInitialPlayerResponse\"\s*:\s*(\{.+?\})\s*,\s*\"ytInitialData\"",
        ]

        for pattern in patterns:
            match = re.search(pattern, html, flags=re.DOTALL)
            if not match:
                continue

            content = match.group(1)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                continue

        raise ValueError("无法从页面中提取 YouTube 播放信息")

    def _pick_cover_url(self, video_details: dict) -> str:
        thumbnails = video_details.get("thumbnail", {}).get("thumbnails", [])
        if not thumbnails:
            return ""
        return thumbnails[-1].get("url", "")

    def _pick_best_video_url(self, formats: list[dict]) -> str:
        if not formats:
            return ""

        progressive_mp4 = []
        mp4_video_only = []
        fallback = []

        for fmt in formats:
            parsed_url = self._extract_format_url(fmt)
            if not parsed_url:
                continue

            mime_type = fmt.get("mimeType", "")
            has_video = "video/" in mime_type or fmt.get("vcodec", "") != "none"
            if not has_video:
                continue

            has_audio = "audio/" in mime_type or fmt.get("acodec", "") not in ("", "none")
            is_mp4 = "video/mp4" in mime_type or fmt.get("ext", "") == "mp4"
            height = fmt.get("height") or 0
            bitrate = fmt.get("bitrate") or fmt.get("averageBitrate") or 0
            score = (height, bitrate)

            if is_mp4 and has_audio:
                progressive_mp4.append((score, parsed_url))
            elif is_mp4:
                mp4_video_only.append((score, parsed_url))
            else:
                fallback.append((score, parsed_url))

        if progressive_mp4:
            return max(progressive_mp4, key=lambda item: item[0])[1]
        if mp4_video_only:
            return max(mp4_video_only, key=lambda item: item[0])[1]
        if fallback:
            return max(fallback, key=lambda item: item[0])[1]
        return ""

    def _extract_format_url(self, fmt: dict) -> str:
        if fmt.get("url"):
            return fmt["url"]

        cipher = fmt.get("signatureCipher") or fmt.get("cipher")
        if not cipher:
            return ""

        params = parse_qs(cipher)
        url = params.get("url", [""])[0]
        if url:
            return unquote(url)
        return ""

    def _extract_video_id(self, share_url: str) -> str:
        parsed = urlparse(share_url)
        host = parsed.netloc.lower()

        if "youtu.be" in host:
            video_id = parsed.path.strip("/").split("/")[0]
            if video_id:
                return video_id

        if "youtube.com" in host:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
                if video_id:
                    return video_id

            shorts_match = re.match(r"^/shorts/([A-Za-z0-9_-]{6,})", parsed.path)
            if shorts_match:
                return shorts_match.group(1)

            embed_match = re.match(r"^/embed/([A-Za-z0-9_-]{6,})", parsed.path)
            if embed_match:
                return embed_match.group(1)

            live_match = re.match(r"^/live/([A-Za-z0-9_-]{6,})", parsed.path)
            if live_match:
                return live_match.group(1)

        if re.fullmatch(r"[A-Za-z0-9_-]{11}", share_url):
            return share_url

        raise ValueError(f"无法从 URL 中提取 YouTube 视频ID: {share_url}")

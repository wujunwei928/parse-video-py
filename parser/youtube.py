import asyncio
import re
from urllib.parse import parse_qs, urlparse

from .base import BaseParser, VideoAuthor, VideoInfo


class YouTube(BaseParser):
    """
    YouTube 解析器
    基于 yt-dlp 抽取媒体信息与可下载直链
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        video_id = self._extract_video_id(share_url)
        return await self.parse_video_id(video_id)

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        page_url = f"https://www.youtube.com/watch?v={video_id}"
        info = await asyncio.to_thread(self._extract_info, page_url)

        formats = info.get("formats", [])
        video_url = self._pick_best_video_url(formats) or info.get("url", "")
        if not video_url:
            raise ValueError("无法获取 YouTube 视频直链")

        thumbnails = info.get("thumbnails", [])
        cover_url = ""
        if thumbnails:
            cover_url = thumbnails[-1].get("url", "")
        if not cover_url:
            cover_url = info.get("thumbnail", "")

        author = VideoAuthor(
            uid=info.get("channel_id", "") or info.get("uploader_id", ""),
            name=info.get("channel", "") or info.get("uploader", ""),
            avatar="",
        )

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=info.get("title", ""),
            author=author,
        )

    def _extract_info(self, page_url: str) -> dict:
        try:
            from yt_dlp import YoutubeDL
        except ImportError as err:
            raise ImportError(
                "缺少依赖 yt-dlp，请先安装后再使用 YouTube 解析功能"
            ) from err

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)

        if not info:
            raise ValueError("无法解析 YouTube 视频信息")

        if info.get("entries"):
            entries = [item for item in info["entries"] if item]
            if not entries:
                raise ValueError("解析到空视频列表")
            info = entries[0]

        return info

    def _pick_best_video_url(self, formats: list[dict]) -> str:
        if not formats:
            return ""

        mp4_with_audio = []
        mp4_video_only = []
        fallback = []

        for fmt in formats:
            url = fmt.get("url")
            if not url:
                continue

            vcodec = fmt.get("vcodec", "")
            acodec = fmt.get("acodec", "")
            ext = fmt.get("ext", "")
            height = fmt.get("height") or 0
            tbr = fmt.get("tbr") or 0
            score = (height, tbr)

            if vcodec != "none" and acodec != "none" and ext == "mp4":
                mp4_with_audio.append((score, url))
            elif vcodec != "none" and ext == "mp4":
                mp4_video_only.append((score, url))
            elif vcodec != "none":
                fallback.append((score, url))

        if mp4_with_audio:
            return max(mp4_with_audio, key=lambda item: item[0])[1]
        if mp4_video_only:
            return max(mp4_video_only, key=lambda item: item[0])[1]
        if fallback:
            return max(fallback, key=lambda item: item[0])[1]
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

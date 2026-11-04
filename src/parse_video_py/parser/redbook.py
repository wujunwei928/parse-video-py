import re

import fake_useragent
import yaml

from ..utils import create_async_client
from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class RedBook(BaseParser):
    """
    小红书
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        headers = {
            # 桌面 UA 的无登录请求会被服务端 302 到登录页，必须使用移动端 UA
            # （os 过滤值区分大小写，数据源中为 iOS/Android）
            "User-Agent": fake_useragent.UserAgent(os=["iOS"]).random,
        }
        async with create_async_client(follow_redirects=True) as client:
            response = await client.get(share_url, headers=headers)
            response.raise_for_status()
        return self._parse_note_info_from_html(response.text)

    @staticmethod
    def _parse_note_info_from_html(html: str) -> VideoInfo:
        """从笔记页 HTML 的 __INITIAL_STATE__ 中提取笔记数据。

        兼容两种页面结构：移动端 noteData.data.noteData（当前返回），
        桌面端 note.noteDetailMap.<noteId>.note（旧结构，保留兼容）。
        """
        pattern = re.compile(
            pattern=r"window\.__INITIAL_STATE__\s*=\s*(.*?)</script>",
            flags=re.DOTALL,
        )
        find_res = pattern.search(html)

        if not find_res or not find_res.group(1):
            raise ValueError("parse video json info from html fail")

        json_data = yaml.safe_load(find_res.group(1).strip())

        data = ((json_data.get("noteData") or {}).get("data") or {}).get("noteData")
        if not isinstance(data, dict):
            note = json_data.get("note") or {}
            # 小红书的分享链接有有效期，过期后会返回 undefined
            note_id = note.get("currentNoteId", "")
            if note_id and note_id != "undefined":
                data = ((note.get("noteDetailMap") or {}).get(note_id) or {}).get(
                    "note"
                )
        if not isinstance(data, dict):
            raise ValueError("parse note info from html fail")

        # 视频地址：小红书为 h264 分享流烧录了水印（作者昵称+小红书 logo），
        # h265 转码流无水印，故优先取 h265；老页面可能只有 h264 流，回退兼容
        video_url = ""
        stream = (data.get("video") or {}).get("media", {}).get("stream", {})
        for codec in ("h265", "h264"):
            stream_list = stream.get(codec) or []
            if stream_list:
                video_url = stream_list[0].get("masterUrl", "")
                if video_url:
                    break

        # 获取图集图片地址
        images = []
        if len(video_url) <= 0:
            for img_item in data.get("imageList") or []:
                # 桌面端结构用 urlDefault，移动端结构用 url
                image_url = img_item.get("urlDefault") or img_item.get("url") or ""
                if not image_url:
                    continue
                # 个别图片有水印, 替换图片域名
                image_id = image_url.split("/")[-1].split("!")[0]
                # 如果链接中带有 spectrum/ , 替换域名时需要带上
                spectrum_str = "spectrum/" if "spectrum" in image_url else ""
                new_url = (
                    "https://ci.xiaohongshu.com/notes_pre_post/"
                    + f"{spectrum_str}{image_id}"
                    + "?imageView2/format/jpg"
                )
                img_info = ImgInfo(url=new_url)
                # 如果原图片网址中没有 notes_pre_post 关键字，不支持替换域名，使用原域名
                if "notes_pre_post" not in image_url:
                    img_info.url = image_url
                # 是否有 livephoto 视频地址
                if img_item.get("livePhoto", False):
                    for stream_item in img_item.get("stream", {}).get("h264", []):
                        live_url = stream_item.get("masterUrl", "")
                        if live_url:
                            img_info.live_photo_url = live_url
                images.append(img_info)

        # 无视频且无图片说明页面是空壳（如被风控重定向到登录页），按解析失败处理
        if len(video_url) <= 0 and len(images) <= 0:
            raise ValueError("parse note info from html fail")

        image_list = data.get("imageList") or []
        cover_url = ""
        if image_list:
            cover_url = (
                image_list[0].get("urlDefault") or image_list[0].get("url") or ""
            )

        # 桌面端字段为 nickname，移动端为 nickName
        user = data.get("user") or {}
        video_info = VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=data.get("title", ""),
            images=images,
            author=VideoAuthor(
                uid=user.get("userId", ""),
                name=user.get("nickname") or user.get("nickName", ""),
                avatar=user.get("avatar", ""),
            ),
        )
        return video_info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("小红书暂不支持直接解析视频ID")

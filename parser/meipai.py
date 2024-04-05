import base64
from typing import Dict, List

import fake_useragent
import httpx
from parsel import Selector

from .base import BaseParser, VideoAuthor, VideoInfo


class MeiPai(BaseParser):
    """
    美拍
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": fake_useragent.UserAgent(os=["windows"]).random,
            }
            response = await client.get(share_url, headers=headers)
            response.raise_for_status()

        sel = Selector(response.text)
        video_bs64 = sel.css("#shareMediaBtn::attr(data-video)").get(default="")
        video_url = self.parse_video_bs64(video_bs64)

        video_info = VideoInfo(
            video_url=video_url,
            cover_url=sel.css("#detailVideo img::attr(src)").get(default=""),
            title=sel.css(".detail-cover-title::text").get(default="").strip(),
            author=VideoAuthor(
                uid=sel.css(".detail-name a::attr(href)")
                .get(default="")
                .split("/")[-1],
                name=sel.css(".detail-avatar::attr(alt)").get(default=""),
                avatar="https:" + sel.css(".detail-avatar::attr(src)").get(default=""),
            ),
        )
        return video_info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = f"https://www.meipai.com/video/{video_id}"
        return await self.parse_share_url(req_url)

    def parse_video_bs64(self, video_bs64: str) -> str:
        hex_val = self.get_hex(video_bs64)
        dec_val = self.get_dec(hex_val["hex_1"])
        d_val = self.sub_str(hex_val["str_1"], dec_val["pre"])
        p_val = self.get_pos(d_val, dec_val["tail"])
        kk_val = self.sub_str(d_val, p_val)
        decode_bs64 = base64.b64decode(kk_val)
        video_url = "https:" + decode_bs64.decode("utf-8")
        return video_url

    def get_hex(self, s: str) -> Dict[str, str]:
        hex_val = s[:4]
        str_val = s[4:]
        return {"hex_1": self.reverse_string(hex_val), "str_1": str_val}

    @staticmethod
    def get_dec(hex_val: str) -> Dict[str, List[int]]:
        int_n = int(hex_val, 16)
        str_n = str(int_n)
        length = len(str_n)
        pre = [int(str_n[i]) for i in range(length) if i < length - 2]
        tail = [int(str_n[i]) for i in range(length) if i >= length - 2]
        return {"pre": pre, "tail": tail}

    @staticmethod
    def sub_str(s: str, b: List[int]) -> str:
        index_1 = b[0]
        index_2 = b[0] + b[1]
        c = s[:index_1]
        d = s[index_1:index_2]
        temp = s[index_2:].replace(d, "")
        return c + temp

    @staticmethod
    def get_pos(s: str, b: List[int]) -> List[int]:
        b[0] = len(s) - b[0] - b[1]
        return b

    @staticmethod
    def reverse_string(s: str) -> str:
        return s[::-1]

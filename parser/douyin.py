import json
import re

import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class DouYin(BaseParser):
    """
    抖音 / 抖音火山版
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        if share_url.startswith("https://www.douyin.com/video/"):
            # 支持电脑网页版链接 https://www.douyin.com/video/xxxxxx
            video_id = share_url.strip("/").split("/")[-1]
            iesdouyin_url = self._get_request_url_by_video_id(video_id)
        else:
            # 支持app分享链接 https://v.douyin.com/xxxxxx
            async with httpx.AsyncClient(follow_redirects=False) as client:
                resp = await client.get(share_url, headers=self.get_default_headers())
                iesdouyin_url = resp.headers.get("location")
                video_id = iesdouyin_url.split("?")[0].strip("/").split("/")[-1]
        if "share/slides" in iesdouyin_url:
            return await self.parse_slides(video_id)
        return await self.parse_video(iesdouyin_url, share_url)
        
    async def parse_video(self, iesdouyin_url: str, share_url: str) -> VideoInfo:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(iesdouyin_url, headers=self.get_default_headers())
            
        try:
            response.raise_for_status()
            data = self.format_response(response)
        except Exception as e1:
            try:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(share_url, headers=self.get_default_headers())
                data = self.format_response(response)
            except Exception as e2:
                raise Exception(f"\nreq iesdouyin: {e1}\nreq share_url: {e2}")
        # 获取图集图片地址
        images = []
        # 如果data含有 images，并且 images 是一个列表
        if "images" in data and isinstance(data["images"], list):
            # 获取每个图片的url_list中的第一个元素，非空时添加到images列表中
            for img in data["images"]:
                if (
                    "url_list" in img
                    and isinstance(img["url_list"], list)
                    and len(img["url_list"]) > 0
                    and len(img["url_list"][0]) > 0
                ):
                    images.append(img["url_list"][0])

        # 获取视频播放地址
        video_url = data["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
        # 如果图集地址不为空时，因为没有视频，上面抖音返回的视频地址无法访问，置空处理
        if len(images) > 0:
            video_url = ""

        # 获取重定向后的mp4视频地址
        # 图集时，视频地址为空，不处理
        video_mp4_url = ""
        if len(video_url) > 0:
            video_mp4_url = await self.get_video_redirect_url(video_url)

        video_info = VideoInfo(
            video_url=video_mp4_url,
            cover_url=data["video"]["cover"]["url_list"][0],
            title=data["desc"],
            images=images,
            author=VideoAuthor(
                uid=data["author"]["sec_uid"],
                name=data["author"]["nickname"],
                avatar=data["author"]["avatar_thumb"]["url_list"][0],
            ),
        )
        return video_info
    
    def format_response(self, response):
        pattern = re.compile(
            pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
            flags=re.DOTALL,
        )
        find_res = pattern.search(response.text)

        if not find_res or not find_res.group(1):
            raise ValueError("parse video json info from html fail")

        json_data = json.loads(find_res.group(1).strip())

        # 获取链接返回json数据进行视频和图集判断,如果指定类型不存在，抛出异常
        # 返回的json数据中，视频字典类型为 video_(id)/page
        VIDEO_ID_PAGE_KEY  = "video_(id)/page"
        # 返回的json数据中，视频字典类型为 note_(id)/page
        NOTE_ID_PAGE_KEY = "note_(id)/page"
        if VIDEO_ID_PAGE_KEY  in json_data["loaderData"]:
            original_video_info = json_data["loaderData"][VIDEO_ID_PAGE_KEY]["videoInfoRes"]
        elif NOTE_ID_PAGE_KEY in json_data["loaderData"]:
            original_video_info = json_data["loaderData"][NOTE_ID_PAGE_KEY]["videoInfoRes"]
        else:
            raise Exception("failed to parse Videos or Photo Gallery info from json")

        # 如果没有视频信息，获取并抛出异常
        if len(original_video_info["item_list"]) == 0:
            err_detail_msg = "failed to parse video info from HTML"
            if len(filter_list := original_video_info["filter_list"]) > 0:
                err_detail_msg = filter_list[0]["detail_msg"]
            raise Exception(err_detail_msg)

        return original_video_info["item_list"][0]
        
    async def parse_slides(self, video_id: str) -> VideoInfo:
        url = "https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/"
        params = {
          'aweme_ids': f"[{video_id}]",
          'request_source': "200",
        }
        headers = {
          'User-Agent': "Mozilla/5.0 (Linux; Android 10; VOG-AL00 Build/HUAWEIVOG-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36",
          'Accept': "application/json, text/plain, */*",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            
        data = resp.json()['aweme_details'][0]
        title = data.get('share_info').get("share_desc_info")
        images = []
        # dynamic_images = []
        for image in data.get('images'):
            if video := image.get('video'):
                # dynamic pic
                images.append(video['play_addr']['url_list'][0])
            else:
                images.append(image['url_list'][0])
        
        return VideoInfo(
            title=title,
            video_url="",
            cover_url="",
            images = images
        )
    
    
    async def get_video_redirect_url(self, video_url: str) -> str:
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(video_url, headers=self.get_default_headers())
        # 返回重定向后的地址，如果没有重定向则返回原地址(抖音中的西瓜视频,重定向地址为空)
        return response.headers.get("location") or video_url

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        req_url = self._get_request_url_by_video_id(video_id)
        return await self.parse_share_url(req_url)

    def _get_request_url_by_video_id(self, video_id) -> str:
        return f"https://www.iesdouyin.com/share/video/{video_id}/"

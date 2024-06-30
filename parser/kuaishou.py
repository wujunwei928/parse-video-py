import fake_useragent
import httpx

from .base import BaseParser, VideoAuthor, VideoInfo


class KuaiShou(BaseParser):
    """
    快手
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        user_agent = fake_useragent.UserAgent(os=["ios"]).random

        # 获取跳转前的信息, 从中获取视频ID, cookie
        async with httpx.AsyncClient(follow_redirects=False) as client:
            redirect_response = await client.get(
                share_url,
                headers={
                    "User-Agent": user_agent,
                    "Referer": "https://v.kuaishou.com/",
                },
            )

        redirect_url = redirect_response.headers.get("Location", "")
        if not redirect_url:
            raise Exception("failed to get parse video ID from share URL")

        # redirect_response.cookies 直接用于下面的请求会触发反爬虫验证, 处理成字典没有这个问题
        format_cookie_map = {}
        for cookie_id, cookie_val in redirect_response.cookies.items():
            format_cookie_map[cookie_id] = cookie_val

        video_id = redirect_url.split("?")[0].split("/")[-1]
        post_data = {
            "fid": "0",
            "shareResourceType": "PHOTO_OTHER",
            "shareChannel": "share_copylink",
            "kpn": "KUAISHOU",
            "subBiz": "BROWSE_SLIDE_PHOTO",
            "env": "SHARE_VIEWER_ENV_TX_TRICK",
            "h5Domain": "m.gifshow.com",
            "photoId": video_id,
            "isLongVideo": False,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://m.gifshow.com/rest/wd/photo/info?kpn=KUAISHOU&captchaToken=",
                headers={
                    "Origin": "https://m.gifshow.com",
                    "Referer": redirect_url,
                    "Content-Type": "application/json",
                    "User-Agent": user_agent,
                },
                cookies=format_cookie_map,
                json=post_data,
            )
            response.raise_for_status()

        json_data = response.json()

        # 判断result状态
        if (result_code := json_data["result"]) != 1:
            raise Exception(f"获取作品信息失败:result={result_code}")

        data = json_data["photo"]

        # 获取视频地址
        video_url = ""
        if "mainMvUrls" in data and len(data["mainMvUrls"]) > 0:
            video_url = data["mainMvUrls"][0]["url"]

        # 获取图集
        ext_params_atlas = data.get("ext_params", {}).get("atlas", {})
        atlas_cdn_list = ext_params_atlas.get("cdn", [])
        atlas_list = ext_params_atlas.get("list", [])
        images = []
        if len(atlas_cdn_list) > 0 and len(atlas_list) > 0:
            for atlas in atlas_list:
                images.append(f"https://{atlas_cdn_list[0]}/{atlas}")

        video_info = VideoInfo(
            video_url=video_url,
            cover_url=data["coverUrls"][0]["url"],
            title=data["caption"],
            author=VideoAuthor(
                uid="",
                name=data["userName"],
                avatar=data["headUrl"],
            ),
            images=images,
        )
        return video_info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("快手暂不支持直接解析视频ID")

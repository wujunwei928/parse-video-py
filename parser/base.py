import dataclasses
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict

import fake_useragent


class VideoSource(Enum):
    """
    视频来源：douiyin，kuaishou...
    """

    DouYin = "douyin"  # 抖音 / 抖音火山版（原 火山小视频）
    KuaiShou = "kuaishou"  # 快手
    PiPiXia = "pipixia"  # 皮皮虾
    WeiBo = "weibo"  # 微博
    WeiShi = "weishi"  # 微视
    LvZhou = "lvzhou"  # 绿洲
    ZuiYou = "zuiyou"  # 最右
    QuanMin = "quanmin"  # 度小视(原 全民小视频)
    XiGua = "xigua"  # 西瓜
    LiShiPin = "lishipin"  # 梨视频
    PiPiGaoXiao = "pipigaoxiao"  # 皮皮搞笑
    HuYa = "huya"  # 虎牙
    AcFun = "acfun"  # A站
    DouPai = "doupai"  # 逗拍
    MeiPai = "meipai"  # 美拍
    QuanMinKGe = "quanminkge"  # 全民K歌
    SixRoom = "sixroom"  # 六间房
    XinPianChang = "xinpianchang"  # 新片场
    HaoKan = "haokan"  # 好看视频


@dataclasses.dataclass
class VideoAuthor:
    """
    视频作者信息
    """

    uid: str = ""
    name: str = ""
    avatar: str = ""


@dataclasses.dataclass
class VideoInfo:
    """
    视频信息
    """

    video_url: str
    cover_url: str
    title: str = ""
    music_url: str = ""
    author: VideoAuthor = VideoAuthor()


class BaseParser(ABC):
    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        return {
            "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
        }

    @abstractmethod
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        """
        解析分享链接, 获取视频信息
        :param share_url: 视频分享链接
        :return: VideoInfo
        """
        pass

    @abstractmethod
    async def parse_video_id(self, video_id: str) -> VideoInfo:
        """
        解析视频ID, 获取视频信息
        :param video_id: 视频ID
        :return:
        """
        pass

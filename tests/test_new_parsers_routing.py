from parse_video_py.parser import video_source_info_mapping
from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.cctv import CCTV
from parse_video_py.parser.qqvideo import QQVideo
from parse_video_py.parser.sohu import Sohu


class TestCCTVRouting:
    """测试央视网解析器路由注册"""

    def test_cctv_registered(self):
        assert VideoSource.CCTV in video_source_info_mapping

    def test_cctv_domains(self):
        info = video_source_info_mapping[VideoSource.CCTV]
        assert "tv.cctv.cn" in info["domain_list"]
        assert "tv.cctv.com" in info["domain_list"]

    def test_cctv_parser_class(self):
        info = video_source_info_mapping[VideoSource.CCTV]
        assert info["parser"] is CCTV


class TestQQVideoRouting:
    """测试腾讯视频解析器路由注册"""

    def test_qqvideo_registered(self):
        assert VideoSource.QQVideo in video_source_info_mapping

    def test_qqvideo_domains(self):
        info = video_source_info_mapping[VideoSource.QQVideo]
        assert "v.qq.com" in info["domain_list"]

    def test_qqvideo_parser_class(self):
        info = video_source_info_mapping[VideoSource.QQVideo]
        assert info["parser"] is QQVideo


class TestSohuRouting:
    """测试搜狐视频解析器路由注册"""

    def test_sohu_registered(self):
        assert VideoSource.Sohu in video_source_info_mapping

    def test_sohu_domains(self):
        info = video_source_info_mapping[VideoSource.Sohu]
        assert "tv.sohu.com" in info["domain_list"]
        assert "my.tv.sohu.com" in info["domain_list"]

    def test_sohu_parser_class(self):
        info = video_source_info_mapping[VideoSource.Sohu]
        assert info["parser"] is Sohu

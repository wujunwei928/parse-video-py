from parse_video_py.utils import extract_url


class TestExtractUrl:
    """测试 URL 提取工具函数"""

    def test_sohu_base64_url(self):
        """搜狐 base64 编码 URL 不被截断"""
        url = "https://tv.sohu.com/v/" "dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html"
        assert extract_url(url) == url

    def test_sohu_base64_in_text(self):
        """从混合文本中提取搜狐 base64 URL"""
        text = (
            "看看这个 https://tv.sohu.com/v/"
            "dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html 好看"
        )
        expected = (
            "https://tv.sohu.com/v/" "dXMvMzM1OTQyMjE0LzM5OTU3MTYxMi5zaHRtbA==.html"
        )
        assert extract_url(text) == expected

    def test_regular_url(self):
        """常规 URL 不受影响"""
        url = "https://v.douyin.com/abc123"
        assert extract_url(url) == url

    def test_url_with_query_params(self):
        """带查询参数的 URL"""
        url = "https://v.qq.com/x/page/l3502vppd13.html?ptag=v_qq_com"
        assert extract_url(url) == url

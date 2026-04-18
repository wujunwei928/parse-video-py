import pytest

from parse_video_py.parser.base import VideoSource
from parse_video_py.parser.twitter import Twitter


class TestTwitterToken:
    """测试 token 计算逻辑"""

    def test_get_token_normal_id(self):
        """测试普通推文 ID 的 token 生成"""
        tw = Twitter()
        token = tw._get_token("1849000000000000000")
        assert len(token) > 0

    def test_get_token_short_id(self):
        """测试短 ID 的 token 生成"""
        tw = Twitter()
        token = tw._get_token("123456789")
        assert len(token) > 0

    def test_get_token_long_id(self):
        """测试长 ID 的 token 生成"""
        tw = Twitter()
        token = tw._get_token("1879553847283155177")
        assert len(token) > 0


class TestTwitterExtractTweetId:
    """测试推文 ID 提取"""

    def test_x_com_standard_url(self):
        """测试 x.com 标准链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://x.com/elonmusk/status/1849000000000000000"
        )
        assert tweet_id == "1849000000000000000"

    def test_twitter_com_standard_url(self):
        """测试 twitter.com 标准链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://twitter.com/elonmusk/status/1849000000000000000"
        )
        assert tweet_id == "1849000000000000000"

    def test_url_with_query_params(self):
        """测试带查询参数的链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://x.com/user/status/1849000000000000000?s=20"
        )
        assert tweet_id == "1849000000000000000"

    def test_mobile_twitter_com(self):
        """测试 mobile.twitter.com 链接"""
        tw = Twitter()
        tweet_id = tw._extract_tweet_id(
            "https://mobile.twitter.com/user/status/1849000000000000000"
        )
        assert tweet_id == "1849000000000000000"

    def test_invalid_url(self):
        """测试无效链接"""
        tw = Twitter()
        with pytest.raises(ValueError):
            tw._extract_tweet_id("https://x.com/user/likes")

    def test_empty_string(self):
        """测试空字符串"""
        tw = Twitter()
        with pytest.raises(ValueError):
            tw._extract_tweet_id("")


class TestTwitterVideoSource:
    """测试 VideoSource 枚举值"""

    def test_twitter_video_source_exists(self):
        """测试 Twitter VideoSource 枚举存在"""
        assert VideoSource.Twitter.value == "twitter"

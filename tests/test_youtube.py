from parser.base import VideoSource
from parser.youtube import YouTube


class TestYouTubeExtractVideoId:
    def test_extract_from_watch_url(self):
        parser = YouTube()
        video_id = parser._extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_from_short_url(self):
        parser = YouTube()
        video_id = parser._extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_from_shorts_url(self):
        parser = YouTube()
        video_id = parser._extract_video_id(
            "https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share"
        )
        assert video_id == "dQw4w9WgXcQ"


class TestYouTubeFormatSelection:
    def test_pick_best_mp4_with_audio(self):
        parser = YouTube()
        formats = [
            {
                "url": "https://example.com/360.mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "ext": "mp4",
                "height": 360,
                "tbr": 600,
            },
            {
                "url": "https://example.com/720.mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "ext": "mp4",
                "height": 720,
                "tbr": 1400,
            },
        ]

        best_url = parser._pick_best_video_url(formats)
        assert best_url == "https://example.com/720.mp4"

    def test_extract_format_url_from_signature_cipher(self):
        parser = YouTube()
        fmt = {
            "signatureCipher": (
                "url=https%3A%2F%2Fexample.com%2Fv.mp4%3Fexpire%3D123&sp=sig&s=abcd"
            )
        }
        url = parser._extract_format_url(fmt)
        assert url == "https://example.com/v.mp4?expire=123"


class TestYouTubePageDataParse:
    def test_extract_player_response(self):
        parser = YouTube()
        html = (
            '<script>var ytInitialPlayerResponse = {"videoDetails":{"title":"demo"}};'
            "</script>"
        )
        result = parser._extract_player_response(html)
        assert result["videoDetails"]["title"] == "demo"

    def test_is_playable_for_login_required(self):
        parser = YouTube()
        response = {
            "playabilityStatus": {
                "status": "LOGIN_REQUIRED",
                "reason": "Sign in to confirm you’re not a bot",
            }
        }
        assert parser._is_playable(response) is False
        status, reason = parser._get_playability_error(response)
        assert status == "LOGIN_REQUIRED"
        assert "not a bot" in reason


class TestYouTubeVideoSource:
    def test_youtube_video_source_exists(self):
        assert VideoSource.YouTube.value == "youtube"

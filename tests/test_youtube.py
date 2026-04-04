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


class TestYouTubeVideoSource:
    def test_youtube_video_source_exists(self):
        assert VideoSource.YouTube.value == "youtube"

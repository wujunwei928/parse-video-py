"""小红书解析器回归测试。

对齐 Go 版 parser/redbook_test.go 的 fixture 集，锁定：
1. 移动端新页面结构 noteData.data.noteData（当前线上返回）
2. 桌面端旧结构 note.noteDetailMap.<noteId>.note（保留兼容）
3. 登录页空壳按解析失败处理
4. 视频流优先取 h265 无水印流，仅 h264 时回退
"""

import pytest

from parse_video_py.parser.redbook import RedBook

# 移动端 UA 返回的页面结构：笔记数据位于 noteData.data.noteData
RED_BOOK_MOBILE_HTML = """<html><script>window.__INITIAL_STATE__=
{"noteData":{"data":{"noteData":{
    "title": "移动端笔记标题", "type": "normal",
    "user": {"userId": "uid123", "nickName": "移动端作者",
             "avatar": "https://avatar.example.com/a.jpg"},
    "video": {"media": {"stream": {}}},
    "imageList": [
        {"url": "https://img.example.com/abc/spectrum/file1!h5_1080jpg",
         "livePhoto": false, "stream": {}},
        {"url": "https://img.example.com/abc/spectrum/file2!h5_1080jpg",
         "livePhoto": true,
         "stream": {"h264": [{"masterUrl": "https://v.example.com/livephoto.mp4"}]}}
    ]
}}}}</script></html>"""

# 桌面端页面结构（旧）：笔记数据位于 note.noteDetailMap.<noteId>.note
RED_BOOK_DESKTOP_HTML = """<html><script>window.__INITIAL_STATE__=
{"note": {"currentNoteId": "note1",
    "noteDetailMap": {"note1": {"note": {
    "title": "桌面端笔记标题",
    "user": {"userId": "uid456", "nickname": "桌面端作者",
             "avatar": "https://avatar.example.com/b.jpg"},
    "video": {"media": {"stream":
        {"h264": [{"masterUrl": "https://v.example.com/desktop.mp4"}]}}},
    "imageList": [{"urlDefault":
        "https://img.example.com/notes_pre_post/file3!h5_1080jpg"}]
}}}}}</script></html>"""

# 桌面端图集笔记（旧结构）：带 notes_pre_post 的原图支持换高清域名
RED_BOOK_DESKTOP_GALLERY_HTML = """<html><script>window.__INITIAL_STATE__=
{"note": {"currentNoteId": "note2",
    "noteDetailMap": {"note2": {"note": {
    "title": "桌面端图集",
    "user": {"userId": "uid789", "nickname": "图集作者"},
    "imageList": [{"urlDefault":
        "https://img.example.com/notes_pre_post/file3!h5_1080jpg"}]
}}}}}</script></html>"""

# 登录页空壳：__INITIAL_STATE__ 存在但无笔记数据（桌面 UA 被 302 时会出现）
RED_BOOK_LOGIN_HTML = (
    "<html><script>window.__INITIAL_STATE__="
    '{"global":{"appSettings":{"fakeModalPercent":0.02}}}</script></html>'
)

# 双流视频笔记：小红书服务端为 h264 分享流烧录了水印（作者昵称+小红书 logo）
RED_BOOK_DUAL_STREAM_HTML = """<html><script>window.__INITIAL_STATE__=
{"noteData":{"data":{"noteData":{
    "title": "双流视频笔记",
    "user": {"userId": "u1", "nickName": "a"},
    "video": {"media": {"stream": {
        "h264": [{"masterUrl": "https://v.example.com/watermarked.mp4"}],
        "h265": [{"masterUrl": "https://v.example.com/clean.mp4"}]
    }}},
    "imageList": []
}}}}</script></html>"""

# 仅 h264 流的老页面
RED_BOOK_H264_ONLY_HTML = """<html><script>window.__INITIAL_STATE__=
{"noteData":{"data":{"noteData":{
    "title": "仅h264流",
    "user": {"userId": "u1", "nickName": "a"},
    "video": {"media": {"stream": {
        "h264": [{"masterUrl": "https://v.example.com/legacy.mp4"}]
    }}},
    "imageList": []
}}}}</script></html>"""


class TestRedBookParseNoteInfoFromHtml:
    def test_mobile_structure(self):
        """移动端新结构：noteData.data.noteData，图片用 url，作者用 nickName"""
        info = RedBook._parse_note_info_from_html(RED_BOOK_MOBILE_HTML)
        assert info.title == "移动端笔记标题"
        assert info.author.name == "移动端作者"
        assert info.author.uid == "uid123"
        assert info.video_url == ""
        assert len(info.images) == 2
        # 原图无 notes_pre_post，不支持换域名，使用原 url
        assert (
            info.images[0].url
            == "https://img.example.com/abc/spectrum/file1!h5_1080jpg"
        )
        # livephoto 视频地址
        assert info.images[1].live_photo_url == "https://v.example.com/livephoto.mp4"

    def test_desktop_old_structure(self):
        """桌面端旧结构：note.noteDetailMap.<noteId>.note 仍可解析"""
        info = RedBook._parse_note_info_from_html(RED_BOOK_DESKTOP_HTML)
        assert info.title == "桌面端笔记标题"
        assert info.author.name == "桌面端作者"
        assert info.video_url == "https://v.example.com/desktop.mp4"
        # 视频笔记不收集图集（与 Go 版行为一致）
        assert info.images == []

    def test_desktop_gallery_image_replace(self):
        """桌面端图集：带 notes_pre_post 的原图替换为高清域名"""
        info = RedBook._parse_note_info_from_html(RED_BOOK_DESKTOP_GALLERY_HTML)
        assert info.title == "桌面端图集"
        assert info.video_url == ""
        assert len(info.images) == 1
        assert info.images[0].url == (
            "https://ci.xiaohongshu.com/notes_pre_post/file3?imageView2/format/jpg"
        )

    def test_login_shell_raises(self):
        """登录页空壳（无笔记数据）按解析失败处理"""
        with pytest.raises(ValueError, match="parse note info from html fail"):
            RedBook._parse_note_info_from_html(RED_BOOK_LOGIN_HTML)

    def test_no_initial_state_raises(self):
        """页面无 __INITIAL_STATE__ 时报错"""
        with pytest.raises(ValueError, match="parse video json info from html fail"):
            RedBook._parse_note_info_from_html("<html>empty</html>")

    def test_dual_stream_prefers_h265(self):
        """回归：h264 分享流带服务端烧录水印，必须优先取 h265 无水印流"""
        info = RedBook._parse_note_info_from_html(RED_BOOK_DUAL_STREAM_HTML)
        assert info.video_url == "https://v.example.com/clean.mp4"

    def test_h264_only_fallback(self):
        """仅 h264 流的老页面回退 h264"""
        info = RedBook._parse_note_info_from_html(RED_BOOK_H264_ONLY_HTML)
        assert info.video_url == "https://v.example.com/legacy.mp4"

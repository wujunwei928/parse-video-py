"""Web 层安全测试：Basic Auth 全局覆盖（含 MCP 路径）、半配置拒绝、错误文案收敛。"""

import base64

import httpx
import pytest
from fastapi.testclient import TestClient

import parse_video_py.web as web
from parse_video_py.parser import UnsupportedShareUrlError


@pytest.fixture()
def client():
    return TestClient(web.app)


def _basic_auth_header(username, password):
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


class TestBasicAuthMiddleware:
    """鉴权中间件：成对配置生效、半配置拒绝、未配置开放"""

    def test_open_when_no_credentials(self, client, monkeypatch):
        monkeypatch.delenv("PARSE_VIDEO_USERNAME", raising=False)
        monkeypatch.delenv("PARSE_VIDEO_PASSWORD", raising=False)
        response = client.get("/video/share/url/parse", params={"url": "not-a-url"})
        assert response.status_code == 200

    def test_requires_auth_when_configured(self, client, monkeypatch):
        monkeypatch.setenv("PARSE_VIDEO_USERNAME", "admin")
        monkeypatch.setenv("PARSE_VIDEO_PASSWORD", "secret")
        response = client.get("/video/share/url/parse", params={"url": "x"})
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].startswith("Basic")

    def test_wrong_credentials_rejected(self, client, monkeypatch):
        monkeypatch.setenv("PARSE_VIDEO_USERNAME", "admin")
        monkeypatch.setenv("PARSE_VIDEO_PASSWORD", "secret")
        response = client.get(
            "/video/share/url/parse",
            params={"url": "x"},
            headers=_basic_auth_header("admin", "wrong"),
        )
        assert response.status_code == 401

    def test_correct_credentials_pass(self, client, monkeypatch):
        monkeypatch.setenv("PARSE_VIDEO_USERNAME", "admin")
        monkeypatch.setenv("PARSE_VIDEO_PASSWORD", "secret")
        response = client.get(
            "/video/share/url/parse",
            params={"url": "not-a-url"},
            headers=_basic_auth_header("admin", "secret"),
        )
        assert response.status_code == 200

    def test_non_ascii_credentials_rejected_not_500(self, client, monkeypatch):
        """非 ASCII 凭据必须走受控 401（回归：compare_digest 的 str 重载会抛 TypeError）"""
        monkeypatch.setenv("PARSE_VIDEO_USERNAME", "admin")
        monkeypatch.setenv("PARSE_VIDEO_PASSWORD", "secret")
        response = client.get(
            "/video/share/url/parse",
            params={"url": "x"},
            headers=_basic_auth_header("用户名", "密码"),
        )
        assert response.status_code == 401

    def test_arbitrary_bytes_credentials_rejected_not_500(self, client, monkeypatch):
        """凭据段含任意二进制字节（非法 UTF-8）时也必须 401 而不是 500"""
        monkeypatch.setenv("PARSE_VIDEO_USERNAME", "admin")
        monkeypatch.setenv("PARSE_VIDEO_PASSWORD", "secret")
        raw = b"\xff\xfe\x00admin:\x01\x02secret"
        credentials = base64.b64encode(raw).decode()
        response = client.get(
            "/video/share/url/parse",
            params={"url": "x"},
            headers={"Authorization": f"Basic {credentials}"},
        )
        assert response.status_code == 401

    def test_half_configured_rejects_everything(self, client, monkeypatch):
        """只配置密码：fail closed，全部 401"""
        monkeypatch.delenv("PARSE_VIDEO_USERNAME", raising=False)
        monkeypatch.setenv("PARSE_VIDEO_PASSWORD", "secret")
        response = client.get(
            "/video/share/url/parse",
            params={"url": "x"},
            headers=_basic_auth_header("admin", "secret"),
        )
        assert response.status_code == 401

    def test_mcp_endpoint_covered_by_auth(self, client, monkeypatch):
        """MCP 挂载点也必须经过鉴权，不能绕过"""
        monkeypatch.setenv("PARSE_VIDEO_USERNAME", "admin")
        monkeypatch.setenv("PARSE_VIDEO_PASSWORD", "secret")
        response = client.post("/mcp", json={}, headers={})
        assert response.status_code == 401

        response = client.get("/mcp")
        assert response.status_code == 401

    def test_mcp_endpoint_open_when_no_auth(self, client, monkeypatch):
        monkeypatch.delenv("PARSE_VIDEO_USERNAME", raising=False)
        monkeypatch.delenv("PARSE_VIDEO_PASSWORD", raising=False)
        response = client.get("/mcp")
        assert response.status_code != 401


class TestErrorMessageHygiene:
    """错误响应不回显上游 URL、内部异常细节"""

    def test_generic_error_does_not_leak_details(self, client, monkeypatch):
        async def boom(url):
            raise Exception("upstream https://internal.example/api?token=SECRET failed")

        monkeypatch.setattr(web, "parse_video_share_url", boom)
        response = client.get(
            "/video/share/url/parse", params={"url": "https://v.douyin.com/abc/"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 500
        assert body["msg"] == "解析失败，请确认链接或视频 ID 后重试"
        assert "internal.example" not in response.text
        assert "SECRET" not in response.text

    def test_unsupported_share_url_message_kept(self, client, monkeypatch):
        async def boom(url):
            raise UnsupportedShareUrlError("分享链接不属于支持的平台")

        monkeypatch.setattr(web, "parse_video_share_url", boom)
        response = client.get(
            "/video/share/url/parse", params={"url": "https://v.douyin.com/abc/"}
        )
        assert response.json()["msg"] == "分享链接不属于支持的平台"

    def test_timeout_message(self, client, monkeypatch):
        async def boom(url):
            raise httpx.ReadTimeout("timed out reading https://upstream.example/x")

        monkeypatch.setattr(web, "parse_video_share_url", boom)
        response = client.get(
            "/video/share/url/parse", params={"url": "https://v.douyin.com/abc/"}
        )
        assert response.json()["msg"] == "解析超时"

    def test_video_id_parse_generic_error(self, client, monkeypatch):
        async def boom(source, video_id):
            raise Exception("internal detail with https://api.example/token=1")

        monkeypatch.setattr(web, "parse_video_id", boom)
        response = client.get(
            "/video/id/parse",
            params={"source": "douyin", "video_id": "123"},
        )
        assert response.json()["msg"] == "解析失败，请确认链接或视频 ID 后重试"
        assert "api.example" not in response.text

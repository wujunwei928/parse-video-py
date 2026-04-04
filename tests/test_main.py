from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_share_url_parse_returns_400_when_no_url_found():
    response = client.get("/video/share/url/parse", params={"url": "这不是链接"})

    assert response.status_code == 200
    assert response.json() == {"code": 400, "msg": "未检测到有效的分享链接"}

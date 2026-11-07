import base64
import dataclasses
import os
import secrets
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi_mcp import FastApiMCP

from parse_video_py import VideoSource, parse_video_id, parse_video_share_url
from parse_video_py.outbound import ResponseTooLargeError
from parse_video_py.parser import UnsupportedShareUrlError
from parse_video_py.utils import extract_url


def _get_templates_dir() -> str:
    # 模板已移入 src/parse_video_py/templates/，与 web.py 同级
    templates_dir = Path(__file__).parent / "templates"
    if templates_dir.is_dir():
        return str(templates_dir)
    raise FileNotFoundError("templates 目录未找到")


class BasicAuthMiddleware:
    """全局 Basic Auth 中间件，覆盖全部路由与 MCP 挂载点。

    - 用户名/密码均已配置：所有请求要求 Basic Auth
    - 只配置其一：视为配置错误，一律 401（fail closed），不再静默开放
    - 均未配置：公开访问
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        username = os.getenv("PARSE_VIDEO_USERNAME")
        password = os.getenv("PARSE_VIDEO_PASSWORD")
        if username and password:
            authorized = await self._check_credentials(scope)
            if not authorized:
                response = JSONResponse(
                    {"code": 401, "msg": "未授权访问"},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="parse-video-py"'},
                )
                await response(scope, receive, send)
                return
        elif username or password:
            # 只配置了用户名或密码其一：拒绝所有请求，避免静默开放
            response = JSONResponse(
                {"code": 401, "msg": "服务鉴权配置不完整"},
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="parse-video-py"'},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _check_credentials(scope) -> bool:
        auth_header = None
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                auth_header = value
                break
        if not auth_header or not auth_header.startswith(b"Basic "):
            return False
        try:
            decoded = base64.b64decode(auth_header[6:], validate=True)
        except ValueError:  # binascii.Error 是其子类
            return False
        # 全程按 bytes 比较：compare_digest 的 str 重载不接受非 ASCII，
        # 攻击者提交任意字节凭据时必须走受控 401 而不是 TypeError → 500
        credentials, _, user_password = decoded.partition(b":")
        username = os.getenv("PARSE_VIDEO_USERNAME", "").encode("utf-8")
        password = os.getenv("PARSE_VIDEO_PASSWORD", "").encode("utf-8")
        return secrets.compare_digest(credentials, username) and secrets.compare_digest(
            user_password, password
        )


def parse_error_message(err: Exception) -> str:
    """对外错误文案：不回显上游 URL、内部异常细节。"""
    if isinstance(err, UnsupportedShareUrlError):
        return str(err)
    if isinstance(err, httpx.TimeoutException):
        return "解析超时"
    if isinstance(err, ResponseTooLargeError):
        return "上游响应超出大小限制"
    return "解析失败，请确认链接或视频 ID 后重试"


app = FastAPI()

# 全局 Basic Auth：覆盖业务路由与 MCP 挂载点
app.add_middleware(BasicAuthMiddleware)

mcp = FastApiMCP(app)
mcp.mount_http()

templates = Jinja2Templates(directory=_get_templates_dir())


@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "github.com/wujunwei928/parse-video-py Demo",
        },
    )


@app.get("/video/share/url/parse")
async def share_url_parse(url: str):
    video_share_url = extract_url(url)
    if video_share_url is None:
        return {
            "code": 400,
            "msg": "未检测到有效的分享链接",
        }

    try:
        video_info = await parse_video_share_url(video_share_url)
        return {
            "code": 200,
            "msg": "解析成功",
            "data": dataclasses.asdict(video_info),
        }
    except Exception as err:
        return {
            "code": 500,
            "msg": parse_error_message(err),
        }


@app.get("/video/id/parse")
async def video_id_parse(source: VideoSource, video_id: str):
    try:
        video_info = await parse_video_id(source, video_id)
        return {
            "code": 200,
            "msg": "解析成功",
            "data": dataclasses.asdict(video_info),
        }
    except Exception as err:
        return {
            "code": 500,
            "msg": parse_error_message(err),
        }


mcp.setup_server()

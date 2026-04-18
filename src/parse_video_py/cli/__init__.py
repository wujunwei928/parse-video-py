"""parse-video-py CLI 工具"""

import typer

app = typer.Typer(
    name="parse-video-py",
    help="视频解析工具，支持 20+ 平台去水印解析",
    add_completion=False,
)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    pass


@app.command()
def version():
    """显示版本信息"""
    typer.echo("parse-video-py 0.0.2")


@app.command()
def parse(
    urls: list[str] = typer.Argument(None, help="视频分享链接"),
    fmt: str = typer.Option("text", "--format", help="输出格式: json, text"),
    file: str = typer.Option(None, "--file", "-f", help="从文件读取链接（每行一个，- 代表 stdin）"),
):
    """解析视频分享链接，支持单条和多条"""
    from parse_video_py.cli._parse import run_parse

    run_parse(urls, fmt, file)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="服务监听地址"),
    port: int = typer.Option(8000, "--port", "-p", help="服务监听端口"),
):
    """启动 HTTP 解析服务"""
    # 延迟导入 uvicorn，避免只安装 .[cli] 时因缺少 uvicorn 导致整个 CLI 崩溃
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "错误: uvicorn 未安装。请使用 parse-video-py[web] 安装 Web 服务依赖",
            err=True,
        )
        raise typer.Exit(code=1)
    uvicorn.run(
        "parse_video_py.web:app",
        host=host,
        port=port,
        reload=False,
    )

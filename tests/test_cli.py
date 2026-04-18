"""CLI 模块单元测试"""

from typer.testing import CliRunner

from parse_video_py.cli import app

runner = CliRunner()


class TestVersionCommand:
    """测试 version 子命令"""

    def test_version_output(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "parse-video-py" in result.output
        assert "0.0.3" in result.output


class TestParseCommand:
    """测试 parse 子命令"""

    def test_parse_no_args_shows_error(self):
        result = runner.invoke(app, ["parse"])
        assert result.exit_code != 0

    def test_parse_invalid_format(self):
        result = runner.invoke(app, ["parse", "https://example.com", "--format", "xml"])
        assert result.exit_code != 0
        assert "不支持的输出格式" in result.output or "xml" in result.output


class TestHelpOutput:
    """测试帮助信息"""

    def test_main_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "parse-video-py" in result.output or "视频解析" in result.output

    def test_parse_help(self):
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0

    def test_serve_help(self):
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output

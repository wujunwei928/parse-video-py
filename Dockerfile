FROM python:3.13-slim

# 安装 uv（固定版本，避免 :latest 漂移；升级时同步修改此 tag）
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

# 设置工作目录
WORKDIR /app

# 复制项目文件（templates 已在 src/parse_video_py/templates/ 中）
COPY pyproject.toml .
COPY src/ src/

# 使用 uv 安装依赖（包含所有可选依赖）
RUN uv pip install --system ".[all]"

# 以非 root 用户运行
RUN useradd --create-home --uid 1001 appuser
USER appuser

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 应用
CMD ["uvicorn", "parse_video_py.web:app", "--host", "0.0.0.0", "--port", "8000"]

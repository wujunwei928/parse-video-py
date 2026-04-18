FROM python:3.10-slim

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 设置工作目录
WORKDIR /app

# 复制项目文件（templates 已在 src/parse_video_py/templates/ 中）
COPY pyproject.toml .
COPY src/ src/

# 使用 uv 安装依赖（包含所有可选依赖）
RUN uv pip install --system ".[all]"

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 应用
CMD ["uvicorn", "parse_video_py.web:app", "--host", "0.0.0.0", "--port", "8000"]

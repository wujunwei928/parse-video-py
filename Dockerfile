# 使用 Python 官方镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录下的相关文件到容器的工作目录
COPY ./parser /app/parser
COPY ./templates /app/templates
COPY ./utils /app/utils
COPY ./requirements.txt /app/
COPY ./main.py /app/


# 安装 Python 应用程序所需的依赖包
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 FastAPI 应用程序的端口
EXPOSE 8000

# 启动 FastAPI 应用程序
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

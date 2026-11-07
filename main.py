import uvicorn

from parse_video_py.web import app

if __name__ == "__main__":
    # 本地演示入口的既定默认值，对外部署走 cli serve / Docker（可用 --host 收窄）
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104

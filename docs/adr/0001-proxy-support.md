# 统一代理支持

所有解析器的 HTTP 请求通过 `utils.py` 中的 `create_async_client()` 工厂函数创建 httpx client，从环境变量 `PARSE_VIDEO_PROXY` 读取代理地址并注入。仅支持 HTTP/HTTPS 代理协议，不支持 SOCKS。代理不可用时直接失败，不静默降级为直连。

**为什么用 client 工厂而不是环境变量透传：** 项目有 36 个独立的 `httpx.AsyncClient()` 调用点散落在 26 个解析器中。直接用 `HTTP_PROXY` 全局变量会代理同进程内所有 HTTP 流量（包括 FastAPI 自身可能的请求），副作用不可控。工厂函数提供了可控的注入点，未来加超时、重试等逻辑也有统一入口。

**为什么不做代理池轮换：** 单代理覆盖大部分场景。需要轮换时，前置一个代理池服务（如 Squid、tinyproxy）比在代码里实现更可靠，也避免引入状态管理。

**为什么不支持 SOCKS：** 视频解析场景中 SOCKS 代理使用率极低，加 `httpx[socks]` 依赖增加维护负担。后续有需求可加可选依赖组 `[socks]`。

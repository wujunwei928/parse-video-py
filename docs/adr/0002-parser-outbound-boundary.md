# 解析与下载的出站边界

对齐 Go 版 parse-video 的同类决策（其 docs/adr/0002）：所有解析器出站请求收敛到 `create_async_client(source=...)` 工厂，由 `outbound.py` 的 `CheckedAsyncTransport` 统一实施边界——平台入口在 `parser/__init__.py` 按 URL 主机名做 DNS 标签边界的后缀最长匹配（拒绝 userinfo、非默认端口、非 http(s)）；每一跳请求（含重定向）必须落在该平台「分享域名 + 上游域名」白名单内；直连时目标主机解析出的全部 IP 必须是公网地址；跨主机跳转剥离 Cookie/Authorization/Referer；响应体限制 16 MiB、总超时 30s、重定向最多 10 跳。Web 层 Basic Auth 下沉为全局 ASGI 中间件（覆盖 MCP 挂载点），半配置一律 401；错误响应不回显内部细节。

**为什么边界放在 transport 而不是每个解析器自查：** 25 个解析器、37 个请求调用点，且 httpx 在 client 层跟随重定向（每跳都会重新经过 transport）。入口校验管住「用户给什么」，transport 管住「实际连什么」，两层缺一不可——`weibo.py`/`redbook.py` 直接 GET 用户原始 URL 的回退路径靠 transport 兜底。

**为什么接受 DNS 校验的 TOCTOU 残留（与 Go 的差异）：** Go 在拨号层校验并按已验证 IP 直连，彻底消除 DNS 重绑定窗口；Python 侧 httpx 不支持 SNI 与 URL host 分离的按 IP 直连，自写底层连接成本过高。本实现是「发送前解析并校验全部 IP」，存在校验后、连接前的重绑定小窗口。白名单已把目标限定在平台自有域名，攻击者需先控制平台权威 DNS 才能利用，风险可接受。若未来需要根除，可在 transport 内按已验证 IP 重写连接目标。

**为什么代理模式跳过本地 DNS 校验：** 与 ADR 0001 一致，代理是部署者显式指定的受信出口，实际出口 IP 由代理侧约束；代理故障保持失败、不回退直连。

**为什么响应上限按原始字节计（不按解压后）：** httpx 在 client 层解压，transport 只能看到压缩流。残余风险是白名单内 CDN 的 gzip 炸弹（解压后远超 16 MiB）；上游均为平台自有 CDN，属低概率场景。若需收紧，可在 transport 层强制 `Accept-Encoding: identity`（会改变请求指纹，未采用）。

**为什么保留 acfun 对 tools.thatwind.com 的第三方依赖：** Python 版 acfun 解析依赖该第三方 API（Go 版直连 acfun.cn），属既有功能行为；将其显式纳入 AcFun 上游白名单并在此记录，替换为官方接口时应同步删除该白名单条目。

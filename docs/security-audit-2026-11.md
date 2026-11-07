# 安全审计报告（2026-11）

以 Go 版 parse-video 提交 `c3ac331`（fix(security): 加固视频解析与下载边界，2026-11-07）为基线，逐类核查本仓库的同类问题并完成修复。本文档是审计结论与修复验收的最终记录。

## 结论速览

| # | Go 版修复的问题 | 审计时本仓库状态 | 处置 |
|---|---|---|---|
| F1 | 平台路由子串匹配 | 存在（`if domain in share_url`） | 已修复：host 后缀最长匹配 |
| F2 | 出站零边界（SSRF） | 存在（无白名单/无 IP 校验/无大小限制/无超时） | 已修复：CheckedAsyncTransport |
| F3 | 直接请求用户原始 URL 并跟随重定向 | 存在（weibo/redbook 回退路径） | 随 F1/F2 收敛 |
| F4 | 无超时 | 存在 | 已修复：30s 总 / 10s 连接 |
| F5 | 无响应大小限制 | 存在 | 已修复：16 MiB |
| F6 | 重定向跨主机不剥敏感头 | 存在 | 已修复（httpx 不自动生成 Referer，仅剥离显式设置的头） |
| F7 | 错误响应回显内部细节 | 存在（`str(err)`） | 已修复：固定文案映射 |
| F8 | Web 前端 DOM XSS | 存在（jQuery `.html()` 拼接未转义字段） | 已修复：DOM API + safeMediaURL |
| F9 | 鉴权覆盖缺口 | 存在（MCP 挂载点无鉴权） | 已修复：全局 Basic Auth 中间件 |
| F10 | Basic Auth 半配置即全开放 | 存在（与 Go 修复前逐字相同） | 已修复：半配置 401 + CLI 拒绝启动 |
| F12 | CDN 资源无 SRI | 存在（5 个资源） | 已修复（jquery 哈希经 cdnjs sha512 交叉验证） |
| F13 | pre-commit 无安全扫描 | 存在 | 已修复：gitleaks / bandit（pre-commit 阶段）；pip-audit 接入 manual 阶段（见暂缓项说明） |
| — | CLI 下载覆盖 | 不适用（无下载功能） | 无动作 |
| — | 代理故障回退直连 | 无此问题（代理失败直接抛错） | 无动作 |
| — | 硬编码会话 | 无真实凭据（sohu api_key 为平台公共前端 key，Go 版保留同值） | 无动作 |

## 架构决策

出站边界的实现层次、DNS 校验的 TOCTOU 残留、代理模式行为等取舍记录在 `docs/adr/0002-parser-outbound-boundary.md`。相关术语见根目录 `CONTEXT.md`。

## 暂缓项（审计发现、本次不修）

- F11 uvicorn 超时调优：keep-alive 已有默认值，收益低。
- F14 IP 限流：需引入新依赖（Go 版有），建议另行评估 slowapi。
- 遗留 requirements.txt 锁有带已知 CVE 的旧版本（starlette==0.37.2、Jinja2==3.1.3、python-multipart==0.0.20 等）。pip-audit 钩子因此接在 manual 阶段（`pre-commit run pip-audit --all-files` 手动执行）；刷新该文件后方可提升为 pre-commit 阶段。
- `video_id` 未编码拼入上游 API URL 路径：host 已被出站白名单钉死，仅能在同一 API 主机内操控路径，低危已知边界。

## 第二轮审计：依赖与 Python 版本（同日）

对实际安装的依赖做 pip-audit（OSV/PyPI advisory，环境模式）：**无已知漏洞**。2026 年近期爆发的高危 CVE 逐项核对均已被当前版本覆盖：Starlette「BadHost」CVE-2026-48710（< 1.0.1，CISA KEV；装 1.10.0，且本服务鉴权不依赖 Host 头）、CVE-2026-48817/54283；MCP Python SDK CVE-2026-52869（< 1.27.2 高危认证绕过）/59950/116685（装 1.30.0，且自建出站边界的每跳校验与跨主机剥头比 SDK 默认更严）；lxml CVE-2026-41066（< 6.1.0，装 6.1.3）。fastapi-mcp 0.4.0 即当前最新。

**Python 3.10 已于 2026-10-01 EOL**（不再收安全补丁），据此完成升级：`Dockerfile` 基镜像 `python:3.10-slim` → `python:3.13-slim`（与开发环境一致）、新增非 root `appuser`、uv 镜像固定 `0.4.4`；两个 CI 工作流 Python 3.10 → 3.13；`requires-python >= 3.10` → `>= 3.12`；移除声明未使用的 aiohttp 依赖；`.gitignore` 补 `.v2c/`、`.video_agent/` 会话产物。另实测 `extract_url` 正则回溯为线性（50KB 恶意输入 0.19ms），无 ReDoS。

升级验证：本地 `pytest` 157 通过、flake8/bandit 通过；Docker 镜像实际构建成功，容器内确认 `uid=1001(appuser)`、`Python 3.13.18`，端到端复验开放模式 400 信封、伪装 URL 固定文案拒绝、鉴权模式无凭据 401、MCP 端点 401。

## 验证记录

- `pytest tests/`：157 通过 / 0 失败（含 `tests/test_outbound.py`、`tests/test_web_security.py` 新增 40+ 安全用例：域名伪装、后缀冒充、userinfo、非默认端口、私网/特殊网段、重定向每跳拒绝、跨主机敏感头剥离、content-length 与流式双重响应上限、代理模式跳过 DNS 校验、鉴权三态、MCP 路径覆盖、错误文案不泄露内部信息、非 ASCII/二进制凭据受控 401）。
- `pre-commit run bandit --all-files`：Passed（6 处既有行为以 `# nosec` 内联豁免并注明理由：cli/main 的 `0.0.0.0` 既定默认、douyin/weibo 解析回退的静默 except）。
- `pre-commit run gitleaks --all-files`：Passed（无硬编码密钥）。
- flake8 / black / isort：全部通过。
- 端到端（uvicorn 实进程）：无凭据开放、完整凭据 401/200、半配置全量 401、`POST /mcp` 无凭据 401、伪装 URL（`evil.com/?x=weibo.com`）返回固定文案、CLI 半配置退出码 1、非 ASCII 与二进制凭据 401（不产生 500）。
- pip-audit（manual 阶段钩子）：本机执行超时未完成（网络受限），属未验证项；配置已按官方 README 接线。

## Code review 轮次（同日）

对上述未提交改动做了独立 code review，两个安全发现已修复并入本轮验证：

- Basic Auth 凭据比较改为全程 bytes：`compare_digest` 的 str 重载不接受非 ASCII，攻击者提交非 ASCII/二进制凭据会触发 TypeError → 500，违背 fail-closed；现一律走受控 401（`web.py` `_check_credentials`）。
- `create_async_client` 统一 `trust_env=False`：修复 source=None 路径仍读取 `HTTP(S)_PROXY` 环境变量、与「出口代理只认 `PARSE_VIDEO_PROXY`」（ADR 0001/0002）不一致的问题。
- 另按仓库约定将词汇表命名为 `CONTEXT.md`（原误用 `GLOSSARY.md`）、`CLAUDE.md` 架构清单收录 `outbound.py` 并在「Adding New Platforms」补充 `UPSTREAM_DOMAINS` 步骤、删除无调用者的 `is_supported_share_url()`。

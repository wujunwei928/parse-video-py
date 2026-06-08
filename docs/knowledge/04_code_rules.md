---
knowledge_version: 1
last_scanned_at: 2026-06-08
source_commit: dd55df3
---

# 编码规则

## 通用原则

- 不做无需求的大重构。
- 不引入不必要的新依赖。
- 优先复用现有组件和工具函数。
- 新增代码必须放在已有目录体系内。
- 禁止绕过统一错误处理。
- 禁止硬编码密钥、配置。

## 目录放置规则

| 代码类型 | 应放位置 | 参考文件 | 禁止放置 |
|---|---|---|---|
| 新平台解析器 | `src/parse_video_py/parser/<平台名>.py` | `parser/douyin.py` | 根目录、其他模块 |
| 解析器路由注册 | `parser/__init__.py` 的 `video_source_info_mapping` | `parser/__init__.py:29` | 单独文件 |
| CLI 命令 | `src/parse_video_py/cli/__init__.py` 注册 | `cli/__init__.py` | 独立入口文件 |
| CLI 核心逻辑 | `src/parse_video_py/cli/_parse.py` | `cli/_parse.py` | `__init__.py` 内联 |
| 工具函数 | `src/parse_video_py/utils.py` | `utils.py` | 解析器内定义 |
| 测试用例 | `tests/test_<模块名>.py` | `tests/test_utils.py` | src 目录内 |
| Web 模板 | `src/parse_video_py/templates/` | `templates/index.html` | 项目根目录 |
| 类型定义/枚举 | `parser/base.py` | `parser/base.py:VideoSource` | 分散到各解析器 |

## 命名规则

- 解析器类名：大驼峰，与 `VideoSource` 枚举值对应（如 `DouYin`、`WeiBo`、`RedBook`）
- 解析器文件名：小写，与类名对应（如 `douyin.py`、`weibo.py`、`redbook.py`）
- `VideoSource` 枚举值：大驼峰（如 `DouYin`、`KuaiShou`）
- 域名列表 key：`domain_list`，值为字符串列表
- URL 查询参数提取：使用 `utils.py:get_val_from_url_by_query_key()`
- 异步方法：统一使用 `async def`

## 错误处理规则

- 解析器内部抛出 `ValueError`（参数错误）或 `Exception`（解析失败）
- Web 层在路由 handler 中用 `try/except` 捕获，返回 `{"code": 500, "msg": str(err)}`
- CLI 层：单条失败输出到 stderr，批量解析继续执行其余 URL
- 解析器路由层：找不到匹配平台抛 `ValueError("share url does not have source config")`

## 日志规则

当前项目未发现统一日志框架。解析器直接使用 `print()` 或异常传递。

## 配置读取规则

- 仅有的配置通过环境变量读取：`PARSE_VIDEO_USERNAME`、`PARSE_VIDEO_PASSWORD`
- 读取方式：`os.getenv()` → `web.py:34-35`
- 禁止硬编码平台 API URL 中的可变部分

## 前端规则

项目有一个单页面 Web 界面（`templates/index.html`），用于展示解析功能。

## 后端规则

- 框架：FastAPI
- 路由定义：函数级装饰器 `@app.get()`
- 依赖注入：`Depends()` 用于 Basic Auth
- 响应格式：`{"code": int, "msg": str, "data": dict}`
- 数据序列化：`dataclasses.asdict(video_info)`
- 解析器模式：
  1. 继承 `BaseParser`
  2. 实现 `async def parse_share_url(self, share_url: str) -> VideoInfo`
  3. 实现 `async def parse_video_id(self, video_id: str) -> VideoInfo`
  4. 使用 `httpx.AsyncClient(follow_redirects=True)` 发请求
  5. UA 伪装：`fake_useragent.UserAgent(os="iOS").random`（桌面端解析器用 `os="windows"`）

## 数据库规则

当前项目未发现数据库相关代码。

## AI 调用规则

当前项目未发现 AI 调用相关代码。MCP 集成是暴露解析能力给 AI 工具调用，不是调用 AI。

## 测试规则

- 框架：pytest + pytest-asyncio
- 目录：`tests/`
- 配置：`pyproject.toml` 的 `[tool.pytest.ini_options]`，`asyncio_mode = "auto"`
- 运行：`pytest tests/ -v --tb=short`
- Mock 策略：对平台 HTTP 响应进行 mock（见 `tests/` 下的测试文件）
- CI 集成：GitHub Actions `python-app.yml` 自动运行测试

## 事实来源

- `pyproject.toml`（依赖、构建、测试配置）
- `src/parse_video_py/parser/base.py`（BaseParser 接口定义）
- `src/parse_video_py/web.py`（路由、鉴权模式）
- `src/parse_video_py/cli/`（CLI 结构）
- `.pre-commit-config.yaml`（代码质量工具配置）

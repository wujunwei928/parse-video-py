# 迁移设计：从 parse-video (Go) 迁移 QQ/搜狐/CCTV 解析器 + Skill

## 背景

Go 项目 `/code/parse-video` 在 commit `19193850ecc33eceb991bea0766f81dd3f2c0014` 之后新增了三个视频解析器和一个 Skill 文件。需要将这些功能迁移到本 Python 项目中。

## 迁移范围

| 内容 | 源文件 (Go) | 目标文件 (Python) |
|------|------------|------------------|
| 腾讯视频解析器 | `parser/qqvideo.go` | `src/parse_video_py/parser/qqvideo.py` |
| 搜狐视频解析器 | `parser/sohu.go` | `src/parse_video_py/parser/sohu.py` |
| 央视网解析器 | `parser/cctv.go` | `src/parse_video_py/parser/cctv.py` |
| Skill 文件 | `.claude/skills/analyze-video-url/SKILL.md` | `.claude/skills/analyze-video-url/SKILL.md` |
| 枚举注册 | `parser/vars.go` | `src/parse_video_py/parser/base.py` |
| 映射注册 | `parser/vars.go` | `src/parse_video_py/parser/__init__.py` |
| QQ 测试 | `parser/qqvideo_test.go` | `tests/test_qqvideo.py` |
| 搜狐测试 | `parser/sohu_test.go` | `tests/test_sohu.py` |
| CCTV 测试 | `parser/cctv_test.go` | `tests/test_cctv.py` |

## 迁移方案

**方案 A：逐平台手动翻译**（已选定）

将 Go 解析器逐个翻译为 Python 异步版本，严格遵循现有 Python 项目风格。

### 语言转换规则

| Go | Python |
|----|--------|
| `resty.New()` | `httpx.AsyncClient()` |
| `regexp.MustCompile()` | `re.compile()` |
| `gjson.Get()` | 标准 JSON 字典访问 |
| `url.Parse()` | `urllib.parse.urlparse()` |
| `base64.StdEncoding.DecodeString()` | `base64.b64decode()` |
| `errors.New()` | `raise ValueError/Exception()` |
| `func (x type) method()` | `async def method(self)` |
| 零值结构体 | 继承 `BaseParser` |

## 解析器设计

### 1. 腾讯视频 (QQVideo)

**URL 模式**：
- PC 端：`v.qq.com/x/page/{vid}.html` 或 `v.qq.com/x/cover/{cid}/{vid}.html`
- 移动端：`m.v.qq.com/x/m/play?vid={vid}`

**解析流程**：
1. `_extract_vid(raw_url)` 从 URL 提取视频 ID
2. `parse_share_url(share_url)` → 调用 `_extract_vid` → `parse_video_id`
3. `parse_video_id(video_id)` → 请求 `https://vv.video.qq.com/getinfo` API
4. 去除 JSONP 包装 `QZOutputJson=` 和尾部分号
5. 从响应中提取 `vl.vi[0]` 的 CDN 地址、fn、fvkey
6. 拼接视频地址：`baseUrl + fn + ?vkey=fvkey`
7. 构造封面图：`https://puui.qpic.cn/vpic_cover/{vid}/{vid}_hz.jpg/496`

**域名**：`v.qq.com`

### 2. 搜狐视频 (Sohu)

**URL 模式**：
- `tv.sohu.com/v/{base64}.html`（base64 解码后为 `us/{uid}/{vid}.shtml`）
- `my.tv.sohu.com/us/{uid}/{vid}.shtml`

**解析流程**：
1. `_extract_vid(raw_url)` 处理两种 URL 格式
2. base64 格式：正则提取 → base64 解码 → 从解码路径提取 vid
3. 直链格式：正则从路径提取 vid
4. `parse_video_id(video_id)` → 请求 `https://api.tv.sohu.com/v4/video/info/{vid}.json`
5. 视频地址优先 `url_high_mp4`，回退 `download_url`
6. 提取作者信息（user_id、nickname、small_pic）

**域名**：`tv.sohu.com`、`my.tv.sohu.com`

### 3. 央视网 (CCTV)

**URL 模式**：
- `tv.cctv.cn`、`tv.cctv.com` 页面中嵌入视频 GUID

**解析流程**：
1. `parse_share_url(share_url)` → 请求页面 HTML → 正则提取 GUID
2. 正则：`var\s+guid\s*=\s*"([^"]+)"`
3. `parse_video_id(guid)` → 请求 `https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}`
4. 检查 status 为 `"001"`
5. 取 `hls_url`（其他高码率流有帧级加扰，花屏）
6. 作者名取自 `play_channel` 字段

**域名**：`tv.cctv.cn`、`tv.cctv.com`

## 注册变更

### base.py - VideoSource 枚举

新增三个值：
```python
QQVideo = "qqvideo"      # 腾讯视频
Sohu = "sohu"            # 搜狐视频
CCTV = "cctv"            # 央视网
```

### __init__.py - 映射注册

新增 import 和 `video_source_info_mapping` 条目，按字母序插入。

## Skill 文件适配

将 `.claude/skills/analyze-video-url/SKILL.md` 从 Go 项目复制并适配：

- 代码路径引用从 Go 改为 Python（`parser/vars.go` → `parser/__init__.py` 等）
- 数据结构引用适配（`VideoParseInfo` → `VideoInfo`）
- 工具链引用适配（`resty` → `httpx`，`gjson` → 标准 JSON）
- 解析器模板从 Go 改为 Python async BaseParser 风格
- 测试框架从 `go test` 改为 `pytest`
- 核心分析流程（渠道判断、重定向、报告生成）保持不变

## 测试设计

每个解析器编写纯单元测试（不依赖外部网络），参考 `tests/test_twitter.py` 模式。

### test_qqvideo.py
- `TestQQVideoExtractVid`：PC 端 page/cover 链接、移动端链接、无效链接、空字符串
- `TestQQVideoVideoSource`：验证枚举值

### test_sohu.py
- `TestSohuExtractVid`：base64 编码 URL、直链 URL、无效 URL、非搜狐链接
- `TestSohuVideoSource`：验证枚举值

### test_cctv.py
- `TestCCTVExtractGuid`：标准格式、无 GUID、空 GUID
- `TestCCTVVideoSource`：验证枚举值

## 不迁移的内容

- Go 项目的 `pre-commit` 配置（Python 项目有自己的 pre-commit）
- Go 项目的 `templates/index.html` 正则修复（Python 项目前端独立）
- Go 项目的设计文档（`docs/superpowers/plans/` 和 `docs/superpowers/specs/`）
- Go 项目的 `README.md` 变更

# JavaScript / Cloudflare Worker 移植

**Issue**: #79
**Date**: 2026-05-23

## 请求

将项目转译为 JavaScript，支持部署到 Cloudflare Workers。

## 拒绝理由

- **本质上是新项目，不是 enhancement**：24 个平台解析器、路由系统、Web 层、CLI 全部需要用另一种语言重写，工作量等同于从零开始
- **核心依赖不兼容**：项目深度依赖 Python 生态库（httpx 异步 HTTP、parsel+lxml HTML 解析、jmespath JSON 查询），Cloudflare Workers 环境不支持 lxml 且有执行时间和包大小限制
- **与项目定位冲突**：本项目是 `parse-video-py`（Python 实现），JavaScript 版本应作为独立仓库存在
- **社区可自行推进**：欢迎社区基于本项目思路新建 JS 仓库，API 接口设计可参考本项目的 FastAPI 端点

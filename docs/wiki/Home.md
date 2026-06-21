# XJGPT School Gateway Wiki

XJGPT School Gateway 是一个面向学校网页版 XipuAI 的 AI 中转站项目。系统把学校提供的网页式 GPT 服务封装为统一 API，同时提供一个仿 ChatGPT 风格的前端界面 XJGPT。

## 项目目标

本项目面向学校 AI 比赛和教学场景，重点展示以下能力：

- 将学校网页版 GPT 封装为统一 API；
- 使用 XJGPT 前端提供类 ChatGPT 的交互体验；
- 支持模型选择，并在 API 调用中区分不同模型；
- 支持 OpenAI-style `messages` 请求格式；
- 记录请求延迟、token 估算和模型调用信息；
- 提供 Python package、Docker image 和 GitHub Release 配置；
- 明确安全边界，避免上传登录状态、私密请求和敏感配置。

## Wiki 导航

- [Quick Start](Quick-Start.md)
- [Architecture](Architecture.md)
- [API Reference](API-Reference.md)
- [Model Selection](Model-Selection.md)
- [XJGPT Frontend](Frontend-XJGPT.md)
- [Packaging and Release](Packaging-and-Release.md)
- [Security Boundary](Security-Boundary.md)
- [Troubleshooting](Troubleshooting.md)

## 核心流程

```text
User
↓
XJGPT Frontend
↓
FastAPI Gateway
↓
Playwright Web Adapter
↓
School XipuAI Web GPT
↓
Gateway returns answer to user
```

用户在 XJGPT 前端输入问题后，前端把请求发送给中转站。中转站完成 API Key 校验、模型参数解析和问题提取，然后通过 Playwright 控制学校 XipuAI 网页提交问题。XipuAI 返回回答后，中转站读取最新回答，并以 JSON 格式返回给用户。

## 当前学校 AI 地址

```text
https://xipuai.xjtlu.edu.cn/v3/chat
```

该地址已经写入 `login_once.py` 和 `school_gpt_adapter.py`。

# Architecture

XJGPT School Gateway 采用前端、后端、中转适配器和学校网页 GPT 四层结构。

## 1. System Overview

```text
┌────────────────────┐
│ User Browser        │
│ XJGPT Frontend      │
└─────────┬──────────┘
          │ HTTP JSON
          ▼
┌────────────────────┐
│ FastAPI Gateway     │
│ /v1/chat            │
│ /v1/chat/completions│
│ /v1/models          │
└─────────┬──────────┘
          │ Playwright call
          ▼
┌────────────────────┐
│ School GPT Adapter  │
│ Web automation      │
│ Model switching     │
│ Answer extraction   │
└─────────┬──────────┘
          │ Browser session
          ▼
┌────────────────────┐
│ XipuAI Web GPT      │
│ School AI website   │
└────────────────────┘
```

## 2. Frontend Layer

前端位于 `static/` 目录：

```text
static/index.html
static/styles.css
static/app.js
```

前端职责：

- 展示 XJGPT 聊天界面；
- 隐藏演示 API Key 输入项；
- 提供模型选择框；
- 将用户输入封装为 OpenAI-style `messages` 请求；
- 调用 `/v1/chat`；
- 渲染中转站返回的回答。

## 3. Gateway Layer

后端入口是 `gateway.py`。

主要接口：

- `GET /`：返回 XJGPT 前端页面；
- `GET /v1/models`：返回可选模型列表；
- `POST /v1/chat`：项目自定义聊天接口；
- `POST /v1/chat/completions`：OpenAI-style 兼容接口；
- `GET /admin/logs`：返回演示日志。

后端职责：

- 校验 `Authorization: Bearer <key>`；
- 解析 `question` 或 `messages`；
- 解析并校验模型 id；
- 调用 `ask_school_gpt(question, model)`；
- 估算 token；
- 记录模型、延迟和长度信息；
- 返回 JSON 结果。

## 4. Web Adapter Layer

网页适配器位于 `school_gpt_adapter.py`。

适配器职责：

- 使用 `school_gpt_state.json` 加载学校 XipuAI 登录状态；
- 打开学校 AI 页面；
- 根据 model 参数尝试切换学校网页模型；
- 查找输入框；
- 填入问题并发送；
- 等待回答区域出现；
- 读取最新 AI 回答；
- 将回答返回给中转站。

## 5. Login State

`login_once.py` 用于手动登录学校 XipuAI 并保存登录状态。

```text
school_gpt_state.json
```

该文件只应保存在本地。项目通过 `.gitignore` 和 release 打包脚本排除该文件。

## 6. Data Flow

```text
1. User submits prompt in XJGPT.
2. Frontend sends JSON to /v1/chat.
3. Gateway validates API key and extracts prompt.
4. Gateway forwards question and model id to adapter.
5. Adapter opens XipuAI with saved login state.
6. Adapter selects model if needed.
7. Adapter sends question to XipuAI.
8. XipuAI generates answer.
9. Adapter reads answer from page.
10. Gateway returns answer, usage estimate and latency.
```

## 7. Design Rationale

学校 XipuAI 主要以网页形式提供服务。项目通过 Web Adapter 把网页交互封装为 API，使前端和第三方系统无需直接处理网页自动化细节。中转站还可以加入统一的鉴权、用量统计、限流和日志治理。

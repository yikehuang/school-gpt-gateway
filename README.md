# XJGPT School Web GPT Gateway

这是一个面向学校网页版 GPT 的 AI 中转站项目。系统把学校 XipuAI 网页版 GPT 封装成统一 API，同时提供一个模仿 ChatGPT 交互风格的前端界面 **XJGPT**。前端或其他系统只需要请求 `/v1/chat`，中转站会完成用户鉴权、模型区分、请求转发、回答读取、token 估算和日志记录。

> 当前分支：`feature/cookie-http-adapter`。该分支在原有 Playwright Web Adapter 基础上，加入了实验性的 Cookie HTTP Adapter，用于在学校授权和本地登录状态有效的前提下，更快地直接调用 XipuAI 后端接口。

## 1. Project Structure

```text
school_gpt_gateway/
├── gateway.py                       # 中转站主程序，同时提供 XJGPT 前端入口
├── adapter_router.py                # 根据环境变量选择 web / cookie 调用模式
├── school_gpt_adapter.py            # 学校网页版 GPT 适配器，包含网页模型选择逻辑
├── school_gpt_cookie_adapter.py     # 实验性 Cookie HTTP Adapter
├── login_once.py                    # 手动登录并保存学校 GPT 登录状态
├── xjgpt_gateway/                   # Python package CLI 入口
├── examples/
│   └── chat_request.example.json    # OpenAI-style 测试 JSON
├── static/
│   ├── index.html                   # XJGPT 前端页面
│   ├── styles.css                   # XJGPT 页面样式
│   └── app.js                       # XJGPT 前端交互逻辑
├── docs/
│   ├── COOKIE_HTTP_ADAPTER.md       # Cookie HTTP Adapter 说明
│   ├── PACKAGING.md                 # 打包说明
│   └── RELEASE.md                   # Release 发布说明
├── scripts/
│   ├── build_release.py             # 本地 release zip 构建脚本
│   └── test_cookie_http_adapter.py  # Cookie HTTP Adapter 本地测试脚本
├── .github/workflows/
│   └── release.yml                  # GitHub tag release workflow
├── .env.cookie.example              # Cookie 模式环境变量模板
├── pyproject.toml                   # Python package 配置
├── MANIFEST.in                      # source distribution 文件清单
├── VERSION
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
└── README.md
```

## 2. Safety Boundary

本项目只适用于学校授权的校内 GPT 环境。项目不绕过登录、不破解验证码、不读取他人 Cookie、不保存真实敏感对话内容。`school_gpt_state.json` 是本地登录状态文件，不应上传到 GitHub。

前端中的演示 API Key 已设置为隐藏输入框，页面不会直接展示该字段。这个处理只适合比赛演示；正式项目不应把真实密钥放在前端代码中，密钥应由后端生成、保存和校验。

`.gitignore` 已加入本地私有 JSON 规则：`*.local.json`、`request.json`、`private_request.json`。如果你有包含隐私内容的测试请求，请使用这些文件名，不要上传到 GitHub。

Cookie HTTP Adapter 只读取你本地 `school_gpt_state.json` 中的登录状态；项目不会打印或上传 cookie 值。该模式需要你在本地配置学校授权的 XipuAI 后端接口。

## 3. Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

也可以用可编辑 package 方式安装：

```bash
pip install -e .
playwright install chromium
```

安装后可以使用命令行入口：

```bash
xjgpt-login
xjgpt-gateway --host 127.0.0.1 --port 8000
```

## 4. Adapter Modes

默认模式是 Playwright Web Adapter：

```bash
export XJGPT_ADAPTER_MODE=web
```

实验性的 Cookie HTTP Adapter：

```bash
export XJGPT_ADAPTER_MODE=cookie
export XIPUAI_CHAT_ENDPOINT="/your/authorized/xipuai/chat/endpoint"
```

Windows PowerShell：

```powershell
$env:XJGPT_ADAPTER_MODE="cookie"
$env:XIPUAI_CHAT_ENDPOINT="/your/authorized/xipuai/chat/endpoint"
```

启动服务后，可以检查当前模式：

```bash
curl http://127.0.0.1:8000/v1/adapter
```

Cookie 模式的详细配置见：

```text
docs/COOKIE_HTTP_ADAPTER.md
```

## 5. School GPT URL

项目当前使用的学校 AI 地址是：

```python
SCHOOL_GPT_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"
```

该地址已经写入 `login_once.py` 和 `school_gpt_adapter.py`。

如果页面选择器不匹配，需要根据 XipuAI 页面修改这些候选选择器：

```python
CHAT_INPUT_SELECTORS = ["textarea", "[contenteditable='true']", "div[role='textbox']"]
SEND_BUTTON_SELECTORS = ["button:has-text('发送')", "button:has-text('Send')", "button[type='submit']"]
ANSWER_SELECTORS = [".assistant-message", ".ai-message", "[class*='assistant']", "[class*='message']"]
```

如果选择器不确定，可以运行：

```bash
playwright codegen https://xipuai.xjtlu.edu.cn/v3/chat
```

## 6. Model Selection

XJGPT 前端右上角已经加入模型选择框。前端会把模型 id 一起发送给 `/v1/chat`。

前端当前使用 OpenAI-style `messages` 请求体：

```json
{
  "model": "school-web-gpt",
  "messages": [
    {
      "content": "请只回复两个字：普通",
      "role": "user"
    }
  ]
}
```

后端也继续兼容旧版简单格式：

```json
{
  "question": "请解释什么是 AI 中转站",
  "model": "gpt-5.4"
}
```

后端当前支持这些模型 id：

```text
auto
school-web-gpt -> 内部等同于 auto，用于兼容 JSON 示例
GPT-5.4        -> model id: gpt-5.4
DeepSeek-R1    -> model id: deepseek-r1
DeepSeek-V3    -> model id: deepseek-v3
Qwen-Max       -> model id: qwen-max
```

`auto` 表示不主动切换学校网页模型，直接使用 XipuAI 当前会话里已经选择的模型。`school-web-gpt` 是接口兼容别名，运行时同样会使用 `auto`。

在 Web Adapter 中，如果你选择 `gpt-5.4`，中转站会尝试在 XipuAI 网页里选择 `GPT-5.4`。在 Cookie HTTP Adapter 中，中转站会把模型 id 放入 HTTP payload；如果学校后端需要真实模型代码，可以用环境变量覆盖，例如：

```bash
export XIPUAI_MODEL_GPT_5_4="real-backend-model-code"
```

## 7. Save Login State

```bash
python login_once.py
```

或使用 package 命令：

```bash
xjgpt-login
```

浏览器打开后，手动登录学校 XipuAI。登录完成并进入聊天页面后，回到终端按 Enter。程序会保存 `school_gpt_state.json`。

## 8. Test Cookie Mode Locally

先检查本地是否有 XipuAI cookie：

```bash
python scripts/test_cookie_http_adapter.py --check-cookies-only
```

配置后端接口后测试实际调用：

```bash
export XJGPT_ADAPTER_MODE=cookie
export XIPUAI_CHAT_ENDPOINT="/your/authorized/xipuai/chat/endpoint"
python scripts/test_cookie_http_adapter.py --question "请只回复两个字：成功" --model auto
```

## 9. Start Gateway and Frontend

```bash
uvicorn gateway:app --host 0.0.0.0 --port 8000
```

或使用 package 命令：

```bash
xjgpt-gateway --host 127.0.0.1 --port 8000
```

启动后，在浏览器打开：

```text
http://127.0.0.1:8000
```

你会看到 XJGPT 前端页面。默认演示 API Key 是：

```text
sk-student-demo-001
```

该 Key 在前端界面中隐藏，不会作为可见输入项展示。

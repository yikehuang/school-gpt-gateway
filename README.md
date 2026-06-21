# XJGPT School Web GPT Gateway

这是一个面向学校网页版 GPT 的 AI 中转站项目。系统把学校 XipuAI 网页版 GPT 封装成统一 API，同时提供一个模仿 ChatGPT 交互风格的前端界面 **XJGPT**。前端或其他系统只需要请求 `/v1/chat`，中转站会完成用户鉴权、模型区分、请求转发、回答读取、token 估算和日志记录。

## 1. Project Structure

```text
school_gpt_gateway/
├── gateway.py              # 中转站主程序，同时提供 XJGPT 前端入口
├── school_gpt_adapter.py   # 学校网页版 GPT 适配器，包含模型选择逻辑
├── login_once.py           # 手动登录并保存学校 GPT 登录状态
├── examples/
│   └── chat_request.example.json  # OpenAI-style 测试 JSON
├── static/
│   ├── index.html          # XJGPT 前端页面
│   ├── styles.css          # XJGPT 页面样式
│   └── app.js              # XJGPT 前端交互逻辑
├── requirements.txt
├── .gitignore
└── README.md
```

## 2. Safety Boundary

本项目只适用于学校授权的校内 GPT 网页环境。项目不绕过登录、不破解验证码、不读取他人 Cookie、不保存真实敏感对话内容。`school_gpt_state.json` 是本地登录状态文件，不应上传到 GitHub。

前端中的演示 API Key 已设置为隐藏输入框，页面不会直接展示该字段。这个处理只适合比赛演示；正式项目不应把真实密钥放在前端代码中，密钥应由后端生成、保存和校验。

`.gitignore` 已加入本地私有 JSON 规则：`*.local.json`、`request.json`、`private_request.json`。如果你有包含隐私内容的测试请求，请使用这些文件名，不要上传到 GitHub。

## 3. Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## 4. School GPT URL

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

## 5. Model Selection

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

如果学校页面中的模型名称和代码不一致，修改 `school_gpt_adapter.py` 中的 `MODEL_LABELS` 即可：

```python
MODEL_LABELS = {
    "auto": None,
    "gpt-5.4": "GPT-5.4",
    "deepseek-r1": "DeepSeek-R1",
    "deepseek-v3": "DeepSeek-V3",
    "qwen-max": "Qwen-Max",
}
```

如果模型下拉框无法自动点击，需要用 `playwright codegen` 获取模型按钮和选项的真实选择器，然后更新 `MODEL_MENU_SELECTORS`。

## 6. Save Login State

```bash
python login_once.py
```

浏览器打开后，手动登录学校 XipuAI。登录完成并进入聊天页面后，回到终端按 Enter。程序会保存 `school_gpt_state.json`。

## 7. Start Gateway and Frontend

```bash
uvicorn gateway:app --host 0.0.0.0 --port 8000
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

## 8. Test API

### 8.1 使用上传的 JSON 格式测试 `/v1/chat`

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d @examples/chat_request.example.json
```

### 8.2 使用 OpenAI-style endpoint 测试 `/v1/chat/completions`

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d @examples/chat_request.example.json
```

### 8.3 使用旧版 question 格式测试

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"请解释什么是 AI 中转站\",\"model\":\"gpt-5.4\"}"
```

查看可选模型：

```bash
curl http://127.0.0.1:8000/v1/models
```

## 9. Admin Logs

```bash
curl http://127.0.0.1:8000/admin/logs \
  -H "Authorization: Bearer admin-demo-key"
```

日志会记录 `requested_model`、`runtime_model` 和 `model_name`，用于区分不同模型的调用情况。

## 10. XJGPT Frontend

XJGPT 前端位于 `static/` 目录。界面包含侧边栏、新建会话、历史会话、隐藏演示 API Key、模型选择框、消息区、推荐问题和底部输入框。前端会调用同源接口 `/v1/chat`，并把用户输入转换成 OpenAI-style `messages` 请求体。中转站再通过 Web Adapter 访问学校 XipuAI 网页，读取回答并返回给前端。

## 11. Competition Explanation

本项目面向学校网页版 GPT 设计中转站和 XJGPT 前端。由于学校 GPT 主要以网页形式提供服务，系统使用 Web Adapter 把网页交互封装为统一 API。用户请求进入中转站后，系统先校验 API Key，再根据前端选择的模型 id 尝试切换学校 XipuAI 网页模型，随后提交问题并读取回答。系统同时记录模型、token 估算、响应耗时和调用状态，展示了校内模型资源统一接入、权限管理、模型路由和用量治理能力。

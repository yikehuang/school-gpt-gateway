# School Web GPT Gateway

这是一个面向学校网页版 GPT 的 AI 中转站项目。系统把学校网页版 GPT 封装成统一 API，前端或其他系统只需要请求 `/v1/chat`，中转站会完成用户鉴权、请求转发、回答读取、token 估算和日志记录。

## 1. Project Structure

```text
school_gpt_gateway/
├── gateway.py              # 中转站主程序
├── school_gpt_adapter.py   # 学校网页版 GPT 适配器
├── login_once.py           # 手动登录并保存学校 GPT 登录状态
├── requirements.txt
├── .gitignore
└── README.md
```

## 2. Safety Boundary

本项目只适用于学校授权的校内 GPT 网页环境。项目不绕过登录、不破解验证码、不读取他人 Cookie、不保存真实敏感对话内容。`school_gpt_state.json` 是本地登录状态文件，不应上传到 GitHub。

## 3. Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## 4. Configure School GPT URL

在 `login_once.py` 和 `school_gpt_adapter.py` 中修改：

```python
SCHOOL_GPT_URL = "https://your-school-gpt-url.example.com"
```

然后根据学校 GPT 页面修改三个选择器：

```python
CHAT_INPUT_SELECTOR = "textarea"
SEND_BUTTON_SELECTOR = "button[type='submit']"
ANSWER_SELECTOR = ".assistant-message"
```

如果选择器不确定，可以运行：

```bash
playwright codegen https://your-school-gpt-url.example.com
```

## 5. Save Login State

```bash
python login_once.py
```

浏览器打开后，手动登录学校 GPT。登录完成并进入聊天页面后，回到终端按 Enter。程序会保存 `school_gpt_state.json`。

## 6. Start Gateway

```bash
uvicorn gateway:app --host 0.0.0.0 --port 8000
```

## 7. Test API

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"请解释什么是 AI 中转站\"}"
```

## 8. Admin Logs

```bash
curl http://127.0.0.1:8000/admin/logs \
  -H "Authorization: Bearer admin-demo-key"
```

## 9. Competition Explanation

本项目面向学校网页版 GPT 设计 AI 中转站。由于学校 GPT 主要以网页形式提供服务，系统使用 Web Adapter 把网页交互封装为统一 API。用户请求进入中转站后，系统先校验 API Key，再将问题提交至学校 GPT 页面，读取回答后返回给用户。系统同时记录 token 估算、响应耗时和调用状态，展示了校内模型资源统一接入、权限管理和用量治理能力。

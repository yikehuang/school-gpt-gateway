# Troubleshooting

本页记录 XJGPT School Gateway 常见问题和处理方法。

## 1. 前端能打开，但发送问题失败

检查中转站是否运行：

```bash
uvicorn gateway:app --host 0.0.0.0 --port 8000
```

浏览器访问：

```text
http://127.0.0.1:8000/v1/models
```

如果该接口打不开，说明后端没有正常启动。

## 2. `Missing API key`

请求没有带 `Authorization` 头。

正确格式：

```http
Authorization: Bearer sk-student-demo-001
```

## 3. `Invalid API key`

请求里的 key 不在 `gateway.py` 的 `VALID_USER_KEYS` 中。

检查：

```python
VALID_USER_KEYS = {
    "sk-student-demo-001": {
        "user_id": "student_001",
        "daily_limit": 100
    }
}
```

## 4. 打开的是登录页，不是 XipuAI 聊天页

说明登录状态没有保存或已失效。

重新运行：

```bash
python login_once.py
```

或：

```bash
xjgpt-login
```

手动登录后，进入聊天页面，再回到终端按 Enter。

## 5. 找不到输入框

可能是学校网页结构变化，导致输入框选择器不匹配。

解决方法：

```bash
playwright codegen https://xipuai.xjtlu.edu.cn/v3/chat
```

手动点击输入框，复制 Playwright 生成的 locator，更新 `school_gpt_adapter.py` 中的 `CHAT_INPUT_SELECTORS`。

## 6. 找不到发送按钮

当前逻辑优先尝试按 Enter 发送。如果学校网页必须点击按钮，需要更新 `SEND_BUTTON_SELECTORS`。

常见选择器：

```python
SEND_BUTTON_SELECTORS = [
    "button:has-text('发送')",
    "button:has-text('Send')",
    "button[type='submit']",
    "[aria-label*='发送']"
]
```

## 7. 没有识别出 AI 回复区域

可能是 `ANSWER_SELECTORS` 不匹配。

处理方式：

1. 在浏览器里打开 XipuAI；
2. 按 F12；
3. 找到 AI 回答文本所在元素；
4. 复制 class 或定位方式；
5. 更新 `ANSWER_SELECTORS`。

常见候选：

```python
ANSWER_SELECTORS = [
    ".assistant-message",
    ".ai-message",
    "[class*='assistant']",
    "[class*='message']",
    "[data-role='assistant']"
]
```

## 8. 回答被截断

复杂问题生成时间较长，中转站可能提前读取了回答。

可以修改 `school_gpt_adapter.py`：

- 增加等待时间；
- 等待“停止生成”按钮消失；
- 多次读取回答文本，直到文本稳定。

示例思路：

```python
previous = ""
stable_count = 0
for _ in range(30):
    current = await latest_answer_locator.inner_text()
    if current == previous:
        stable_count += 1
    else:
        stable_count = 0
    if stable_count >= 3:
        break
    previous = current
    await page.wait_for_timeout(1000)
```

## 9. 模型无法切换

模型选择器可能不匹配。

运行：

```bash
playwright codegen https://xipuai.xjtlu.edu.cn/v3/chat
```

手动选择目标模型，复制生成的 locator，更新 `MODEL_MENU_SELECTORS` 和 `MODEL_LABELS`。

## 10. GitHub Releases 没有显示

Release 只有 workflow 成功运行后才会出现。

检查：

```text
Actions -> Release
```

如果没有运行，可以手动点击：

```text
Run workflow
```

## 11. GitHub Packages 没有显示

检查：

- Actions 是否成功；
- workflow 是否有 `packages: write` 权限；
- Docker image 是否推送到 `ghcr.io/yikehuang/school-gpt-gateway`；
- package visibility 是否公开；
- Dockerfile 是否设置 `org.opencontainers.image.source`。

## 12. Windows PowerShell JSON 测试失败

PowerShell 中推荐使用：

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/chat" `
  -Method Post `
  -Headers @{Authorization="Bearer sk-student-demo-001"} `
  -ContentType "application/json" `
  -Body (Get-Content ".\examples\chat_request.example.json" -Raw)
```

如果使用 `curl`，Windows 可能调用的是 PowerShell alias，不是原生 curl。可以改用 `curl.exe`。

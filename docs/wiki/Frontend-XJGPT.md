# XJGPT Frontend

XJGPT 是本项目提供的前端界面，风格参考 ChatGPT 的基础布局，包括左侧会话栏、主聊天区、模型选择和底部输入框。

## 1. 文件位置

```text
static/index.html
static/styles.css
static/app.js
```

## 2. 页面结构

前端主要包含：

- 左侧 sidebar；
- XJGPT 标题；
- 新建会话按钮；
- 会话历史列表；
- 右上角模型选择框；
- 中间聊天消息区；
- 底部输入框；
- 发送按钮。

## 3. 请求格式

前端发送请求时使用 OpenAI-style `messages` 格式：

```json
{
  "model": "gpt-5.4",
  "messages": [
    {
      "role": "user",
      "content": "请解释 AI 中转站"
    }
  ]
}
```

请求会发送到：

```text
POST /v1/chat
```

## 4. API Key 隐藏

前端当前隐藏演示 API Key，不在页面上直接展示输入框。比赛演示版使用：

```text
sk-student-demo-001
```

注意：这只是演示方案。正式系统不应把真实 API Key 写入前端代码。正式项目应由后端负责生成、保存、校验和轮换 API Key。

## 5. 模型选择

用户在右上角选择模型后，前端会把对应模型 id 写入请求体。后端根据 model 参数决定是否让网页适配器切换学校 XipuAI 模型。

建议前端显示名称和后端模型 id 对应：

```text
Auto          -> auto
GPT-5.4       -> gpt-5.4
DeepSeek-R1   -> deepseek-r1
DeepSeek-V3   -> deepseek-v3
Qwen-Max      -> qwen-max
```

## 6. 错误显示

如果后端返回错误，前端应显示错误信息，例如：

```text
Missing API key
Invalid API key
Unsupported model
School GPT response timeout
No answer found from school GPT page
```

## 7. 可改进方向

后续可以增强：

- 多轮对话历史持久化；
- Markdown 渲染；
- 代码块复制按钮；
- 流式输出；
- 文件上传；
- 用户登录；
- 每个用户独立 API Key；
- 对话导出；
- 管理后台可视化。

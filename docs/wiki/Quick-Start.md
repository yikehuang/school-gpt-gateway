# Quick Start

本页说明如何在本地运行 XJGPT School Gateway。

## 1. 克隆仓库

```bash
git clone https://github.com/yikehuang/school-gpt-gateway.git
cd school-gpt-gateway
```

## 2. 安装依赖

普通安装方式：

```bash
pip install -r requirements.txt
playwright install chromium
```

可编辑 package 安装方式：

```bash
pip install -e .
playwright install chromium
```

## 3. 登录学校 XipuAI

第一次运行前需要保存学校 XipuAI 登录状态：

```bash
python login_once.py
```

如果已经用 package 方式安装，也可以运行：

```bash
xjgpt-login
```

浏览器打开后，用户需要手动登录学校 XipuAI。进入聊天页面后，回到终端按 Enter。程序会生成：

```text
school_gpt_state.json
```

该文件包含本地登录状态，不能上传到 GitHub。

## 4. 启动中转站

```bash
uvicorn gateway:app --host 0.0.0.0 --port 8000
```

或使用 package 命令：

```bash
xjgpt-gateway --host 127.0.0.1 --port 8000
```

## 5. 打开前端

浏览器访问：

```text
http://127.0.0.1:8000
```

页面会显示 XJGPT 前端。用户可以在页面右上角选择模型，在底部输入框输入问题。

## 6. API 测试

### `/v1/chat`

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d @examples/chat_request.example.json
```

### `/v1/chat/completions`

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d @examples/chat_request.example.json
```

## 7. 常见成功返回

```json
{
  "object": "chat.completion",
  "model": "school-web-gpt",
  "model_name": "Auto",
  "answer": "普通",
  "usage": {
    "input_tokens": 8,
    "output_tokens": 2,
    "total_tokens": 10
  },
  "latency_ms": 5000
}
```

实际回答内容取决于学校 XipuAI 网页端所选模型。

# API Reference

本页说明 XJGPT School Gateway 当前提供的接口。

## 1. Authentication

除前端页面和模型列表外，聊天接口需要请求头：

```http
Authorization: Bearer sk-student-demo-001
```

当前演示 key 写在 `gateway.py` 的 `VALID_USER_KEYS` 中。正式系统应把 API Key 存入数据库，并且只保存哈希值。

## 2. GET `/v1/models`

返回支持的模型列表。

### Request

```bash
curl http://127.0.0.1:8000/v1/models
```

### Response

```json
{
  "object": "list",
  "data": [
    {
      "id": "auto",
      "name": "Auto",
      "description": "Use current model selected in XipuAI"
    },
    {
      "id": "gpt-5.4",
      "name": "GPT-5.4"
    }
  ]
}
```

实际返回以 `gateway.py` 中 `SUPPORTED_MODELS` 为准。

## 3. POST `/v1/chat`

项目自定义聊天接口，支持两种请求格式。

### 3.1 OpenAI-style `messages` 格式

```json
{
  "model": "school-web-gpt",
  "messages": [
    {
      "role": "user",
      "content": "请只回复两个字：普通"
    }
  ]
}
```

测试命令：

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d @examples/chat_request.example.json
```

### 3.2 简单 `question` 格式

```json
{
  "question": "请解释什么是 AI 中转站",
  "model": "gpt-5.4"
}
```

测试命令：

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d '{"question":"请解释什么是 AI 中转站","model":"gpt-5.4"}'
```

### Response

```json
{
  "object": "chat.completion",
  "model": "gpt-5.4",
  "model_name": "GPT-5.4",
  "answer": "AI 中转站用于统一接收、转发和管理模型请求。",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 20,
    "total_tokens": 30
  },
  "latency_ms": 5200
}
```

## 4. POST `/v1/chat/completions`

该接口提供接近 OpenAI Chat Completions 的返回格式。

### Request

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d @examples/chat_request.example.json
```

### Response

```json
{
  "id": "chatcmpl-school-gateway",
  "object": "chat.completion",
  "model": "school-web-gpt",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "普通"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 8,
    "completion_tokens": 2,
    "total_tokens": 10
  }
}
```

## 5. GET `/admin/logs`

返回演示日志。

### Request

```bash
curl http://127.0.0.1:8000/admin/logs \
  -H "Authorization: Bearer admin-demo-key"
```

### Response

```json
{
  "total_requests": 1,
  "logs": [
    {
      "user_id": "student_001",
      "model": "gpt-5.4",
      "model_name": "GPT-5.4",
      "question_length": 10,
      "answer_length": 20,
      "input_tokens": 5,
      "output_tokens": 10,
      "total_tokens": 15,
      "latency_ms": 5000,
      "created_at": 1780000000
    }
  ]
}
```

## 6. Error Responses

常见错误：

```json
{
  "detail": "Missing API key"
}
```

```json
{
  "detail": "Invalid API key"
}
```

```json
{
  "detail": "Unsupported model"
}
```

```json
{
  "detail": "School GPT response timeout"
}
```

错误细节取决于 `gateway.py` 和 `school_gpt_adapter.py` 的实际异常处理。

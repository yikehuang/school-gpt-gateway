# Model Selection

XJGPT School Gateway 支持在前端和 API 调用中区分模型。

## 1. 前端模型选择

XJGPT 前端右上角提供模型下拉框。用户选择模型后，前端会把模型 id 放入请求体。

示例请求：

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

## 2. 后端模型校验

`gateway.py` 中维护支持的模型列表。后端会在请求进入学校网页适配器前校验模型 id。

当前建议保留以下模型：

```text
auto
school-web-gpt
gpt-5.4
deepseek-r1
deepseek-v3
qwen-max
```

其中：

- `auto`：不主动切换学校网页模型，直接使用 XipuAI 当前会话已选模型；
- `school-web-gpt`：兼容别名，内部等同于 `auto`；
- `gpt-5.4`：尝试选择学校网页中的 `GPT-5.4`；
- `deepseek-r1`、`deepseek-v3`、`qwen-max`：预留模型 id，需要与学校网页真实选项匹配。

## 3. 网页模型切换

`school_gpt_adapter.py` 使用 `MODEL_LABELS` 把内部模型 id 映射到学校网页里的模型显示文本。

示例：

```python
MODEL_LABELS = {
    "auto": None,
    "school-web-gpt": None,
    "gpt-5.4": "GPT-5.4",
    "deepseek-r1": "DeepSeek-R1",
    "deepseek-v3": "DeepSeek-V3",
    "qwen-max": "Qwen-Max",
}
```

如果学校网页里的真实名称不同，需要修改右侧显示文本。例如学校网页显示 `GPT-5.4 Turbo`，则可以改成：

```python
"gpt-5.4": "GPT-5.4 Turbo"
```

## 4. 选择器调试

如果模型无法自动切换，需要用 Playwright 录制工具获取真实选择器：

```bash
playwright codegen https://xipuai.xjtlu.edu.cn/v3/chat
```

操作步骤：

1. 打开页面；
2. 手动点击模型选择按钮；
3. 选择目标模型；
4. 查看 Playwright 生成的 locator；
5. 更新 `MODEL_MENU_SELECTORS` 或模型选项选择逻辑。

## 5. API 中区分模型

### `/v1/chat`

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d '{"question":"请解释什么是反向代理","model":"gpt-5.4"}'
```

### `/v1/chat/completions`

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-student-demo-001" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.4","messages":[{"role":"user","content":"请解释什么是反向代理"}]}'
```

## 6. 日志中的模型记录

中转站日志应记录：

```text
model
model_name
latency_ms
input_tokens
output_tokens
total_tokens
```

这样后续可以比较不同模型的响应速度和 token 消耗。

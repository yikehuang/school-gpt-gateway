# XJGPT Frontend API Settings

XJGPT 前端已经把 API 调用配置放入软件设置面板。打开前端后，点击左侧的 **API 调用设置** 或顶部的 **设置**，可以修改以下内容：

- **API Base URL**：后端服务地址。本地运行时可以留空，前端会调用同源后端，例如 `http://127.0.0.1:8000`。
- **Chat Endpoint**：可选择 `/v1/chat` 或 `/v1/chat/completions`。
- **Authorization Bearer Key**：默认演示 Key 为 `sk-student-demo-001`。
- **请求格式**：可选择 OpenAI-style `messages` 或简单 `question` 格式。

## Model Selection Flow

前端右上角的模型下拉框会把选中的 `model` 一起发送给中转站。中转站会在 `gateway.py` 中执行模型校验和别名转换，然后把 runtime model 传给 `school_gpt_adapter.py`。

```text
XJGPT 前端 model
↓
/v1/chat 或 /v1/chat/completions
↓
gateway.py normalize_model()
↓
ask_school_gpt(question, model=runtime_model)
↓
school_gpt_adapter.py 根据 MODEL_LABELS 找到学校网页模型名称
↓
Playwright 尝试在 XipuAI 网页中切换同名模型
```

当前模型映射位于 `school_gpt_adapter.py`：

```python
MODEL_LABELS = {
    "auto": None,
    "gpt-5.4": "GPT-5.4",
    "deepseek-r1": "DeepSeek-R1",
    "deepseek-v3": "DeepSeek-V3",
    "qwen-max": "Qwen-Max",
}
```

如果学校网页里的模型名称和代码中的 label 不一致，需要修改 `MODEL_LABELS` 右侧的显示名称。例如学校网页显示 `DeepSeek R1`，则需要改为：

```python
"deepseek-r1": "DeepSeek R1"
```

## Important Limitation

中转站会尝试让学校 XipuAI 选择和前端一致的模型，但是否真正切换成功取决于学校网页的 DOM 结构和模型菜单选择器。如果运行时报错“没有找到模型选择入口”或“没有找到模型选项”，需要使用：

```bash
playwright codegen https://xipuai.xjtlu.edu.cn/v3/chat
```

录制模型下拉框的真实选择器，然后更新 `MODEL_MENU_SELECTORS`。

## Quick Test

启动服务后，在设置面板点击 **测试 API**。测试请求会发送：

```text
请只回复两个字：成功
```

如果学校 XipuAI 正常返回，说明前端设置、中转站 API 和学校网页适配器已经形成完整调用链。

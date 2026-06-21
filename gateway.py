import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from school_gpt_adapter import ask_school_gpt, list_school_gpt_models, MODEL_LABELS


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="XJGPT School Web GPT Gateway")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


VALID_USER_KEYS = {
    "sk-student-demo-001": {
        "user_id": "student_001",
        "daily_limit": 100
    }
}

BASE_MODEL_OPTIONS = [
    {
        "id": "auto",
        "name": "Auto",
        "description": "使用 XipuAI 网页当前已选择的模型"
    },
    {
        "id": "school-web-gpt",
        "name": "School Web GPT",
        "description": "兼容 JSON 示例中的模型名，内部等同于 auto"
    },
]

LEGACY_MODEL_OPTIONS = [
    {
        "id": "gpt-5.4",
        "name": "GPT-5.4",
        "description": "学校网页中显示的 GPT-5.4 模型"
    },
    {
        "id": "deepseek-r1",
        "name": "DeepSeek-R1",
        "description": "如学校网页提供该模型，可从前端选择"
    },
    {
        "id": "deepseek-v3",
        "name": "DeepSeek-V3",
        "description": "如学校网页提供该模型，可从前端选择"
    },
    {
        "id": "qwen-max",
        "name": "Qwen-Max",
        "description": "如学校网页提供该模型，可从前端选择"
    },
]

MODEL_OPTIONS = BASE_MODEL_OPTIONS + LEGACY_MODEL_OPTIONS
MODEL_ALIASES = {
    "school-web-gpt": "auto",
    "xjgpt": "auto",
    "xipuai": "auto"
}
MODEL_NAME_CACHE = {model["id"]: model["name"] for model in MODEL_OPTIONS}

USAGE_LOGS = []


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    # XJGPT 前端使用的简单格式
    question: Optional[str] = None
    # OpenAI-style / chat-completions 兼容格式
    messages: Optional[List[ChatMessage]] = None
    model: str = "auto"


def estimate_tokens(text: str) -> int:
    """
    比赛演示版 token 估算。
    中文场景可以粗略按字符数 / 2 估算。
    正式系统应使用对应模型 tokenizer。
    """
    return max(1, len(text) // 2)


def normalize_model(model_id: str) -> Tuple[str, str]:
    """Return (requested_model, runtime_model)."""
    requested_model = (model_id or "auto").strip() or "auto"
    runtime_model = MODEL_ALIASES.get(requested_model, requested_model)

    return requested_model, runtime_model


def get_model_name(model_id: str) -> str:
    if model_id in MODEL_NAME_CACHE:
        return MODEL_NAME_CACHE[model_id]
    if model_id == "auto":
        return "Auto"
    if model_id == "school-web-gpt":
        return "School Web GPT"
    label = MODEL_LABELS.get(model_id)
    return label or model_id


def merge_model_options(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = []
    seen = set()

    for group in groups:
        for option in group:
            option_id = option.get("id")
            if not option_id or option_id in seen:
                continue

            seen.add(option_id)
            merged.append(option)

    MODEL_NAME_CACHE.clear()
    MODEL_NAME_CACHE.update({option["id"]: option.get("name", option["id"]) for option in merged})
    return merged


async def get_model_options() -> List[Dict[str, Any]]:
    try:
        school_models = await list_school_gpt_models()
    except Exception:
        school_models = []

    if school_models:
        return merge_model_options(BASE_MODEL_OPTIONS, school_models)

    return merge_model_options(BASE_MODEL_OPTIONS, LEGACY_MODEL_OPTIONS)


def extract_question(request: ChatRequest) -> str:
    if request.question and request.question.strip():
        return request.question.strip()

    if request.messages:
        for message in reversed(request.messages):
            if message.role == "user" and message.content.strip():
                return message.content.strip()

        for message in reversed(request.messages):
            if message.content.strip():
                return message.content.strip()

    raise HTTPException(status_code=400, detail="Question cannot be empty. Provide 'question' or 'messages'.")


def authenticate_user(authorization: str) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    user_key = authorization.replace("Bearer ", "").strip()

    if user_key not in VALID_USER_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return VALID_USER_KEYS[user_key]


async def run_gateway_chat(request: ChatRequest, user: Dict[str, Any]) -> Dict[str, Any]:
    question = extract_question(request)
    requested_model, runtime_model = normalize_model(request.model)

    start_time = time.time()

    try:
        answer = await ask_school_gpt(question, model=runtime_model)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    input_tokens = estimate_tokens(question)
    output_tokens = estimate_tokens(answer)
    total_tokens = input_tokens + output_tokens
    latency_ms = int((time.time() - start_time) * 1000)

    log = {
        "user_id": user["user_id"],
        "requested_model": requested_model,
        "runtime_model": runtime_model,
        "model_name": get_model_name(requested_model),
        "question_length": len(question),
        "answer_length": len(answer),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "created_at": int(time.time())
    }

    USAGE_LOGS.append(log)

    return {
        "object": "chat.completion",
        "model": requested_model,
        "runtime_model": runtime_model,
        "model_name": get_model_name(requested_model),
        "answer": answer,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        },
        "latency_ms": latency_ms
    }


@app.get("/")
async def serve_frontend():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"message": "XJGPT frontend is not installed."}
    return FileResponse(index_file)


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": await get_model_options()
    }


@app.post("/v1/chat")
async def chat(
    request: ChatRequest,
    authorization: str = Header(default="")
) -> Dict[str, Any]:
    user = authenticate_user(authorization)
    return await run_gateway_chat(request, user)


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatRequest,
    authorization: str = Header(default="")
) -> Dict[str, Any]:
    """
    OpenAI-style endpoint for JSON payloads such as:
    {
      "model": "school-web-gpt",
      "messages": [{"role": "user", "content": "请只回复两个字：普通"}]
    }
    """
    user = authenticate_user(authorization)
    result = await run_gateway_chat(request, user)

    created = int(time.time())
    return {
        "id": f"xjgpt-{created}",
        "object": "chat.completion",
        "created": created,
        "model": result["model"],
        "runtime_model": result["runtime_model"],
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result["answer"]
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": result["usage"]["input_tokens"],
            "completion_tokens": result["usage"]["output_tokens"],
            "total_tokens": result["usage"]["total_tokens"]
        },
        "latency_ms": result["latency_ms"]
    }


@app.get("/admin/logs")
def get_logs(authorization: str = Header(default="")):
    if authorization != "Bearer admin-demo-key":
        raise HTTPException(status_code=403, detail="Admin key required")

    return {
        "total_requests": len(USAGE_LOGS),
        "logs": USAGE_LOGS
    }

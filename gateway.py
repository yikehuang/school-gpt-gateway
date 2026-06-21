import time
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from school_gpt_adapter import ask_school_gpt, MODEL_LABELS


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

MODEL_OPTIONS = [
    {
        "id": "auto",
        "name": "Auto",
        "description": "使用 XipuAI 网页当前已选择的模型"
    },
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

SUPPORTED_MODEL_IDS = {model["id"] for model in MODEL_OPTIONS}

USAGE_LOGS = []


class ChatRequest(BaseModel):
    question: str
    model: str = "auto"


def estimate_tokens(text: str) -> int:
    """
    比赛演示版 token 估算。
    中文场景可以粗略按字符数 / 2 估算。
    正式系统应使用对应模型 tokenizer。
    """
    return max(1, len(text) // 2)


def get_model_name(model_id: str) -> str:
    if model_id == "auto":
        return "Auto"
    label = MODEL_LABELS.get(model_id)
    return label or model_id


@app.get("/")
async def serve_frontend():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"message": "XJGPT frontend is not installed."}
    return FileResponse(index_file)


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": MODEL_OPTIONS
    }


@app.post("/v1/chat")
async def chat(
    request: ChatRequest,
    authorization: str = Header(default="")
) -> Dict[str, Any]:

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    user_key = authorization.replace("Bearer ", "").strip()

    if user_key not in VALID_USER_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")

    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    model_id = (request.model or "auto").strip()
    if model_id not in SUPPORTED_MODEL_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model: {model_id}. Use GET /v1/models to check available models."
        )

    user = VALID_USER_KEYS[user_key]
    start_time = time.time()

    try:
        answer = await ask_school_gpt(question, model=model_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    input_tokens = estimate_tokens(question)
    output_tokens = estimate_tokens(answer)
    total_tokens = input_tokens + output_tokens
    latency_ms = int((time.time() - start_time) * 1000)

    log = {
        "user_id": user["user_id"],
        "model": model_id,
        "model_name": get_model_name(model_id),
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
        "model": model_id,
        "model_name": get_model_name(model_id),
        "answer": answer,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        },
        "latency_ms": latency_ms
    }


@app.get("/admin/logs")
def get_logs(authorization: str = Header(default="")):
    if authorization != "Bearer admin-demo-key":
        raise HTTPException(status_code=403, detail="Admin key required")

    return {
        "total_requests": len(USAGE_LOGS),
        "logs": USAGE_LOGS
    }

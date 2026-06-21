import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from school_gpt_adapter import ask_school_gpt


class PowerShellJSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(
    title="School Web GPT Gateway",
    default_response_class=PowerShellJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_user_keys() -> Dict[str, Dict[str, Any]]:
    raw_keys = os.getenv("SCHOOL_GPT_API_KEYS") or os.getenv("SCHOOL_GPT_API_KEY")
    keys = [key.strip() for key in (raw_keys or "").split(",") if key.strip()]

    if not keys:
        keys = ["sk-student-demo-001"]

    return {
        key: {
            "user_id": f"user_{index + 1:03d}",
            "daily_limit": 100,
        }
        for index, key in enumerate(keys)
    }


VALID_USER_KEYS = load_user_keys()
ADMIN_KEY = os.getenv("SCHOOL_GPT_ADMIN_KEY", "admin-demo-key")
USAGE_LOGS = []
DEFAULT_MODEL = "school-web-gpt"


class ChatRequest(BaseModel):
    question: str


class OpenAIMessage(BaseModel):
    role: str
    content: Any = ""


class OpenAIChatRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: List[OpenAIMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 2)


def require_user(authorization: str) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    user_key = authorization.replace("Bearer ", "").strip()

    if user_key not in VALID_USER_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return VALID_USER_KEYS[user_key]


def normalize_content(content: Any) -> str:
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "\n".join(parts)

    return str(content)


def build_prompt(messages: List[OpenAIMessage]) -> str:
    lines = []
    for message in messages:
        role = message.role.lower()
        content = normalize_content(message.content).strip()
        if not content:
            continue

        if role == "system":
            lines.append(f"System instruction:\n{content}")
        elif role == "developer":
            lines.append(f"Developer instruction:\n{content}")
        elif role == "assistant":
            lines.append(f"Assistant:\n{content}")
        else:
            lines.append(f"User:\n{content}")

    return "\n\n".join(lines).strip()


async def ask_and_log(question: str, user: Dict[str, Any]) -> Dict[str, Any]:
    question = question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    start_time = time.time()

    try:
        answer = await ask_school_gpt(question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    input_tokens = estimate_tokens(question)
    output_tokens = estimate_tokens(answer)
    total_tokens = input_tokens + output_tokens
    latency_ms = int((time.time() - start_time) * 1000)

    USAGE_LOGS.append({
        "user_id": user["user_id"],
        "question_length": len(question),
        "answer_length": len(answer),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "created_at": int(time.time()),
    })

    return {
        "answer": answer,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
    }


def build_openai_completion(result: Dict[str, Any], model: str) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model or DEFAULT_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result["answer"],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": result["input_tokens"],
            "completion_tokens": result["output_tokens"],
            "total_tokens": result["total_tokens"],
        },
    }


def chunk_text(text: str, size: int = 24):
    for index in range(0, len(text), size):
        yield text[index:index + size]


async def stream_openai_question(question: str, user: Dict[str, Any], model: str):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    first_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model or DEFAULT_MODEL,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None,
            }
        ],
    }
    yield f"data: {json.dumps(first_chunk, ensure_ascii=True, separators=(',', ':'))}\n\n"

    task = asyncio.create_task(ask_and_log(question, user))
    while not task.done():
        yield ": ping\n\n"
        await asyncio.sleep(2)

    try:
        result = task.result()
    except Exception as exc:
        error_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model or DEFAULT_MODEL,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": f"[gateway error] {exc}"},
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=True, separators=(',', ':'))}\n\n"
        yield "data: [DONE]\n\n"
        return

    for text_chunk in chunk_text(result["answer"]):
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model or DEFAULT_MODEL,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": text_chunk},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=True, separators=(',', ':'))}\n\n"

    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model or DEFAULT_MODEL,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(final_chunk, ensure_ascii=True, separators=(',', ':'))}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat")
async def chat(
    request: ChatRequest,
    authorization: str = Header(default=""),
) -> Dict[str, Any]:
    user = require_user(authorization)
    result = await ask_and_log(request.question.strip(), user)

    return {
        "object": "chat.completion",
        "model": DEFAULT_MODEL,
        "answer": result["answer"],
        "usage": {
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "total_tokens": result["total_tokens"],
        },
        "latency_ms": result["latency_ms"],
    }


@app.get("/v1/models")
def list_models(authorization: str = Header(default="")):
    require_user(authorization)
    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL,
                "object": "model",
                "created": 0,
                "owned_by": "xipu-ai",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def openai_chat_completions(
    request: OpenAIChatRequest,
    authorization: str = Header(default=""),
):
    user = require_user(authorization)
    question = build_prompt(request.messages)

    if not question:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    if request.stream:
        return StreamingResponse(
            stream_openai_question(question, user, request.model),
            media_type="text/event-stream; charset=utf-8",
        )

    result = await ask_and_log(question, user)
    return build_openai_completion(result, request.model)


@app.get("/admin/logs")
def get_logs(authorization: str = Header(default="")):
    if authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="Admin key required")

    return {
        "total_requests": len(USAGE_LOGS),
        "logs": USAGE_LOGS,
    }

import time
from typing import Dict, Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from school_gpt_adapter import ask_school_gpt


app = FastAPI(title="School Web GPT Gateway")


VALID_USER_KEYS = {
    "sk-student-demo-001": {
        "user_id": "student_001",
        "daily_limit": 100
    }
}

USAGE_LOGS = []


class ChatRequest(BaseModel):
    question: str


def estimate_tokens(text: str) -> int:
    """
    比赛演示版 token 估算。
    中文场景可以粗略按字符数 / 2 估算。
    正式系统应使用对应模型 tokenizer。
    """
    return max(1, len(text) // 2)


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

    user = VALID_USER_KEYS[user_key]
    start_time = time.time()

    try:
        answer = await ask_school_gpt(question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    input_tokens = estimate_tokens(question)
    output_tokens = estimate_tokens(answer)
    total_tokens = input_tokens + output_tokens
    latency_ms = int((time.time() - start_time) * 1000)

    log = {
        "user_id": user["user_id"],
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
        "model": "school-web-gpt",
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

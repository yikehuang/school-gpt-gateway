import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from school_gpt_adapter import (
    ask_school_gpt,
    close_school_gpt_login_session,
    get_school_gpt_login_status,
    list_school_gpt_models,
    MODEL_LABELS,
    save_school_gpt_login_session,
    start_school_gpt_login_session,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
GATEWAY_CONFIG_FILE = BASE_DIR / "gateway_config.local.json"
DEFAULT_GATEWAY_CONFIG = {
    "model": "auto",
    "thinking": "minimal"
}

app = FastAPI(title="XJGPT School Web GPT Gateway")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


VALID_USER_KEYS = {
    "sk-student-demo-001": {
        "user_id": "student_001",
        "daily_limit": 100
    }
}

CLIENT_MODEL_OPTIONS = [
    {
        "id": "default",
        "name": "Default",
        "description": "客户端统一填写 default；后端强制使用中转站保存的默认模型",
        "client_only": True
    },
]

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

MODEL_OPTIONS = CLIENT_MODEL_OPTIONS + BASE_MODEL_OPTIONS + LEGACY_MODEL_OPTIONS
THINKING_OPTIONS = [
    {
        "id": "minimal",
        "name": "关闭思考",
        "description": "对应 XipuAI 的 Close Thinking"
    },
    {
        "id": "low",
        "name": "轻量思考",
        "description": "对应 XipuAI 的 Low"
    },
    {
        "id": "medium",
        "name": "均衡模式",
        "description": "对应 XipuAI 的 Medium"
    },
    {
        "id": "high",
        "name": "深度分析",
        "description": "对应 XipuAI 的 High"
    },
]
THINKING_ALIASES = {
    "": "minimal",
    "none": "minimal",
    "off": "minimal",
    "close": "minimal",
    "closed": "minimal",
    "minimal": "minimal",
    "low": "low",
    "medium": "medium",
    "balanced": "medium",
    "balance": "medium",
    "high": "high",
    "deep": "high",
    "关闭思考": "minimal",
    "轻量思考": "low",
    "均衡模式": "medium",
    "深度分析": "high",
}
MODEL_ALIASES = {
    "school-web-gpt": "auto",
    "xjgpt": "auto",
    "xipuai": "auto"
}
MODEL_NAME_CACHE = {model["id"]: model["name"] for model in MODEL_OPTIONS}
THINKING_NAME_CACHE = {option["id"]: option["name"] for option in THINKING_OPTIONS}

USAGE_LOGS = []


class ChatMessage(BaseModel):
    role: str
    content: Any


class ChatRequest(BaseModel):
    # XJGPT 前端使用的简单格式
    question: Optional[str] = None
    # OpenAI-style / chat-completions 兼容格式
    messages: Optional[List[ChatMessage]] = None
    # XipuAI 思考程度：minimal / low / medium / high
    thinking: Optional[str] = None
    # OpenAI-style reasoning effort compatibility.
    reasoning_effort: Optional[str] = None
    reasoning: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    images: Optional[List[Any]] = None


class GatewayConfigRequest(BaseModel):
    model: Optional[str] = None
    thinking: Optional[str] = None
    reasoning_effort: Optional[str] = None
    reasoning: Optional[Dict[str, Any]] = None


def estimate_tokens(text: str) -> int:
    """
    比赛演示版 token 估算。
    中文场景可以粗略按字符数 / 2 估算。
    正式系统应使用对应模型 tokenizer。
    """
    return max(1, len(text) // 2)


def normalize_model_value(model_id: Optional[Any], default_model: str = "auto") -> str:
    raw = model_id if model_id is not None else default_model
    value = str(raw or default_model).strip()
    return value or default_model


def normalize_thinking_value(raw: Optional[Any], default_thinking: str = "minimal") -> str:
    value = raw
    if value is None or str(value).strip() == "":
        value = default_thinking

    key = str(value or "minimal").strip().lower()
    thinking = THINKING_ALIASES.get(key)

    if thinking:
        return thinking

    allowed = ", ".join(option["id"] for option in THINKING_OPTIONS)
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported thinking value: {raw}. Use one of: {allowed}."
    )


def load_gateway_config() -> Dict[str, Any]:
    config = dict(DEFAULT_GATEWAY_CONFIG)

    if GATEWAY_CONFIG_FILE.exists():
        try:
            with GATEWAY_CONFIG_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            data = {}

        if isinstance(data, dict):
            config.update({
                "model": normalize_model_value(data.get("model"), config["model"]),
                "thinking": config["thinking"]
            })

            try:
                config["thinking"] = normalize_thinking_value(data.get("thinking"), config["thinking"])
            except HTTPException:
                config["thinking"] = DEFAULT_GATEWAY_CONFIG["thinking"]

    return config


def save_gateway_config(config: Dict[str, Any]) -> Dict[str, Any]:
    clean_config = {
        "model": normalize_model_value(config.get("model"), DEFAULT_GATEWAY_CONFIG["model"]),
        "thinking": normalize_thinking_value(config.get("thinking"), DEFAULT_GATEWAY_CONFIG["thinking"]),
        "updated_at": int(time.time())
    }

    GATEWAY_CONFIG_FILE.write_text(
        json.dumps(clean_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return clean_config


def config_response(config: Dict[str, Any]) -> Dict[str, Any]:
    requested_model, runtime_model = normalize_model(config.get("model"))
    thinking = normalize_thinking_value(config.get("thinking"), DEFAULT_GATEWAY_CONFIG["thinking"])

    return {
        "object": "gateway.config",
        "data": {
            "model": requested_model,
            "runtime_model": runtime_model,
            "model_name": get_model_name(requested_model),
            "thinking": thinking,
            "thinking_name": get_thinking_name(thinking),
            "config_file": GATEWAY_CONFIG_FILE.name
        }
    }


def normalize_model(model_id: Optional[str], default_model: Optional[str] = None) -> Tuple[str, str]:
    """Return (requested_model, runtime_model)."""
    fallback_model = normalize_model_value(default_model, DEFAULT_GATEWAY_CONFIG["model"])
    requested_model = normalize_model_value(model_id, fallback_model)
    runtime_model = MODEL_ALIASES.get(requested_model, requested_model)

    return requested_model, runtime_model


def resolve_gateway_model(client_model: Optional[str], gateway_config: Dict[str, Any]) -> Tuple[str, str, str]:
    """Return (client_model, configured_model, runtime_model).

    API clients can send any model name, but execution always follows the
    server-side gateway default. This keeps WeFlow and similar tools on a
    stable `default` model while the real upstream model is controlled here.
    """
    normalized_client_model = normalize_model_value(client_model, "default")
    configured_model, runtime_model = normalize_model(None, gateway_config.get("model"))
    return normalized_client_model, configured_model, runtime_model


def get_model_name(model_id: str) -> str:
    if model_id in MODEL_NAME_CACHE:
        return MODEL_NAME_CACHE[model_id]
    if model_id == "default":
        return "Default"
    if model_id == "auto":
        return "Auto"
    if model_id == "school-web-gpt":
        return "School Web GPT"
    label = MODEL_LABELS.get(model_id)
    return label or model_id


def get_thinking_name(thinking: str) -> str:
    return THINKING_NAME_CACHE.get(thinking, thinking)


def normalize_thinking(request: ChatRequest, default_thinking: Optional[str] = None) -> str:
    raw = request.thinking or request.reasoning_effort

    if not raw and isinstance(request.reasoning, dict):
        raw = request.reasoning.get("effort")

    return normalize_thinking_value(raw, default_thinking or DEFAULT_GATEWAY_CONFIG["thinking"])


def is_model_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "没有找到模型" in message or ("model" in message and "not found" in message)


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
        return merge_model_options(CLIENT_MODEL_OPTIONS, BASE_MODEL_OPTIONS, school_models)

    return merge_model_options(CLIENT_MODEL_OPTIONS, BASE_MODEL_OPTIONS, LEGACY_MODEL_OPTIONS)


def coerce_image_input(value: Any) -> Optional[Dict[str, Any]]:
    if not value:
        return None

    if isinstance(value, str):
        return {"url": value}

    if not isinstance(value, dict):
        return None

    if isinstance(value.get("image_url"), dict):
        image = dict(value["image_url"])
        if image.get("url"):
            image.setdefault("detail", value.get("detail"))
            return image

    if isinstance(value.get("image_url"), str):
        return {"url": value["image_url"], "detail": value.get("detail")}

    for key in ("url", "data_url", "base64"):
        if value.get(key):
            return dict(value)

    return None


def extract_content_parts(content: Any) -> Tuple[str, List[Dict[str, Any]]]:
    texts: List[str] = []
    images: List[Dict[str, Any]] = []

    if isinstance(content, str):
        return content.strip(), images

    if isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                if item.strip():
                    texts.append(item.strip())
                continue

            if not isinstance(item, dict):
                continue

            item_type = str(item.get("type") or "").lower()

            if item_type in {"text", "input_text"} or item.get("text"):
                text = str(item.get("text") or "").strip()
                if text:
                    texts.append(text)

            if item_type in {"image_url", "input_image", "image"} or item.get("image_url"):
                image = coerce_image_input(item)
                if image:
                    images.append(image)

        return "\n".join(texts).strip(), images

    if isinstance(content, dict):
        text = str(content.get("text") or content.get("content") or "").strip()
        image = coerce_image_input(content)
        if image:
            images.append(image)
        return text, images

    return "", images


def extract_request_parts(request: ChatRequest) -> Tuple[str, List[Dict[str, Any]]]:
    request_images = [
        image for image in (coerce_image_input(item) for item in (request.images or [])) if image
    ]

    if request.question and request.question.strip():
        return request.question.strip(), request_images

    if request.messages:
        for message in reversed(request.messages):
            if message.role == "user":
                text, images = extract_content_parts(message.content)
                if text or images:
                    return text, request_images + images

        for message in reversed(request.messages):
            text, images = extract_content_parts(message.content)
            if text or images:
                return text, request_images + images

    raise HTTPException(status_code=400, detail="Question cannot be empty. Provide 'question' or 'messages'.")


def extract_question(request: ChatRequest) -> str:
    question, _ = extract_request_parts(request)
    return question


def authenticate_user(authorization: str) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    user_key = authorization.replace("Bearer ", "").strip()

    if user_key not in VALID_USER_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return VALID_USER_KEYS[user_key]


async def run_gateway_chat(request: ChatRequest, user: Dict[str, Any]) -> Dict[str, Any]:
    question, images = extract_request_parts(request)
    if not question and images:
        question = "请描述这张图片。"

    gateway_config = load_gateway_config()
    client_model, requested_model, runtime_model = resolve_gateway_model(request.model, gateway_config)
    thinking = normalize_thinking(request, gateway_config.get("thinking"))
    gateway_model_forced = client_model != requested_model

    start_time = time.time()

    try:
        answer = await ask_school_gpt(question, model=runtime_model, thinking=thinking, images=images)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    input_tokens = estimate_tokens(question) + len(images) * 256
    output_tokens = estimate_tokens(answer)
    total_tokens = input_tokens + output_tokens
    latency_ms = int((time.time() - start_time) * 1000)

    log = {
        "user_id": user["user_id"],
        "client_model": client_model,
        "requested_model": requested_model,
        "runtime_model": runtime_model,
        "model_name": get_model_name(requested_model),
        "thinking": thinking,
        "thinking_name": get_thinking_name(thinking),
        "gateway_model_forced": gateway_model_forced,
        "fallback_model_used": False,
        "question_length": len(question),
        "answer_length": len(answer),
        "image_count": len(images),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "created_at": int(time.time())
    }

    USAGE_LOGS.append(log)

    return {
        "object": "chat.completion",
        "client_model": client_model,
        "model": requested_model,
        "runtime_model": runtime_model,
        "model_name": get_model_name(requested_model),
        "gateway_model_forced": gateway_model_forced,
        "fallback_model_used": False,
        "thinking": thinking,
        "thinking_name": get_thinking_name(thinking),
        "image_count": len(images),
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


@app.get("/v1/thinking")
def list_thinking_options():
    return {
        "object": "list",
        "data": THINKING_OPTIONS
    }


@app.get("/v1/gateway-config")
def get_gateway_config():
    return config_response(load_gateway_config())


@app.get("/v1/school-login/status")
def school_login_status(authorization: str = Header(default="")):
    authenticate_user(authorization)
    return {
        "object": "school.login",
        "data": get_school_gpt_login_status()
    }


@app.post("/v1/school-login/start")
async def start_school_login(authorization: str = Header(default="")):
    authenticate_user(authorization)

    try:
        status = await start_school_gpt_login_session()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "object": "school.login",
        "data": status
    }


@app.post("/v1/school-login/save")
async def save_school_login(authorization: str = Header(default="")):
    authenticate_user(authorization)

    try:
        status = await save_school_gpt_login_session()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "object": "school.login",
        "data": status
    }


@app.post("/v1/school-login/cancel")
async def cancel_school_login(authorization: str = Header(default="")):
    authenticate_user(authorization)
    await close_school_gpt_login_session()
    return {
        "object": "school.login",
        "data": get_school_gpt_login_status()
    }


@app.post("/v1/gateway-config")
def update_gateway_config(
    request: GatewayConfigRequest,
    authorization: str = Header(default="")
):
    authenticate_user(authorization)
    current = load_gateway_config()

    raw_thinking = request.thinking or request.reasoning_effort
    if not raw_thinking and isinstance(request.reasoning, dict):
        raw_thinking = request.reasoning.get("effort")

    config = save_gateway_config({
        "model": normalize_model_value(request.model, current.get("model", DEFAULT_GATEWAY_CONFIG["model"])),
        "thinking": normalize_thinking_value(raw_thinking, current.get("thinking", DEFAULT_GATEWAY_CONFIG["thinking"]))
    })

    return config_response(config)


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
        "client_model": result.get("client_model", "default"),
        "model": result["model"],
        "runtime_model": result["runtime_model"],
        "gateway_model_forced": result.get("gateway_model_forced", True),
        "fallback_model_used": result.get("fallback_model_used", False),
        "image_count": result.get("image_count", 0),
        "thinking": result["thinking"],
        "reasoning_effort": result["thinking"],
        "thinking_name": result["thinking_name"],
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

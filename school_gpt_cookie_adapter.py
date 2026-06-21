import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import httpx


SCHOOL_GPT_BASE_URL = os.getenv("XIPUAI_BASE_URL", "https://xipuai.xjtlu.edu.cn")
SCHOOL_GPT_CHAT_ENDPOINT = os.getenv("XIPUAI_CHAT_ENDPOINT", "")
SCHOOL_GPT_STATE_FILE = os.getenv("XJGPT_STATE_FILE", "school_gpt_state.json")
COOKIE_DOMAIN_KEYWORDS = ["xipuai.xjtlu.edu.cn", "xjtlu.edu.cn"]

# Keep this mapping aligned with school_gpt_adapter.py.
MODEL_LABELS = {
    "auto": None,
    "gpt-5.4": "GPT-5.4",
    "deepseek-r1": "DeepSeek-R1",
    "deepseek-v3": "DeepSeek-V3",
    "qwen-max": "Qwen-Max",
}


class CookieAdapterConfigError(RuntimeError):
    pass


class CookieAdapterResponseError(RuntimeError):
    pass


def _read_storage_state(path: str = SCHOOL_GPT_STATE_FILE) -> Dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        raise CookieAdapterConfigError(
            f"Storage state file not found: {state_path}. Run xjgpt-login first."
        )

    with state_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_cookies_from_storage_state(path: str = SCHOOL_GPT_STATE_FILE) -> Dict[str, str]:
    """
    Load only XipuAI/XJTLU-related cookies from a local Playwright storage_state file.

    The function returns cookie names and values for an HTTP client. It never prints cookie values.
    """
    state = _read_storage_state(path)
    cookies: Dict[str, str] = {}

    for cookie in state.get("cookies", []):
        domain = str(cookie.get("domain", ""))
        name = cookie.get("name")
        value = cookie.get("value")

        if not name or value is None:
            continue

        if any(keyword in domain for keyword in COOKIE_DOMAIN_KEYWORDS):
            cookies[str(name)] = str(value)

    if not cookies:
        raise CookieAdapterConfigError(
            "No XipuAI/XJTLU cookies found in school_gpt_state.json. Run xjgpt-login after logging into XipuAI."
        )

    return cookies


def load_local_storage_value(key: str, path: str = SCHOOL_GPT_STATE_FILE) -> Optional[str]:
    """Optionally read a token-like value from localStorage when the school endpoint requires it."""
    if not key:
        return None

    state = _read_storage_state(path)
    for origin in state.get("origins", []):
        origin_url = str(origin.get("origin", ""))
        if not origin_url.startswith(SCHOOL_GPT_BASE_URL):
            continue

        for item in origin.get("localStorage", []):
            if item.get("name") == key:
                value = item.get("value")
                return str(value) if value is not None else None

    return None


def _build_url(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if not endpoint:
        raise CookieAdapterConfigError(
            "XIPUAI_CHAT_ENDPOINT is not configured. "
            "Set it to the authorized XipuAI backend chat endpoint before using cookie mode."
        )
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return urljoin(SCHOOL_GPT_BASE_URL.rstrip("/") + "/", endpoint.lstrip("/"))


def _model_for_payload(model: str) -> str:
    if model == "auto":
        return os.getenv("XIPUAI_DEFAULT_MODEL", "auto")
    return os.getenv(f"XIPUAI_MODEL_{model.upper().replace('-', '_')}", model)


def build_payload(question: str, model: str = "auto") -> Dict[str, Any]:
    """
    Build a default OpenAI-style payload.

    If the real XipuAI backend expects a different schema, keep this function as the single place to adapt it.
    """
    payload_style = os.getenv("XIPUAI_PAYLOAD_STYLE", "openai").strip().lower()
    runtime_model = _model_for_payload(model)

    if payload_style == "simple":
        return {
            "question": question,
            "model": runtime_model,
        }

    return {
        "model": runtime_model,
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ],
        "stream": False,
    }


def _extract_known_text(data: Any) -> Optional[str]:
    """Extract assistant text from common JSON response shapes."""
    if isinstance(data, str):
        return data.strip() or None

    if isinstance(data, list):
        parts: List[str] = []
        for item in data:
            value = _extract_known_text(item)
            if value:
                parts.append(value)
        return "".join(parts).strip() or None

    if not isinstance(data, dict):
        return None

    for key in ("answer", "content", "text", "response", "message", "result", "output"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        parts: List[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            message = choice.get("message")
            for node in (delta, message, choice):
                value = _extract_known_text(node)
                if value:
                    parts.append(value)
        return "".join(parts).strip() or None

    data_node = data.get("data")
    if data_node is not None:
        return _extract_known_text(data_node)

    return None


def _parse_sse_text(text: str) -> Optional[str]:
    parts: List[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue

        payload = line[len("data:"):].strip()
        if not payload or payload == "[DONE]":
            continue

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            parts.append(payload)
            continue

        value = _extract_known_text(data)
        if value:
            parts.append(value)

    return "".join(parts).strip() or None


def parse_response_text(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "")
    raw_text = response.text.strip()

    if not raw_text:
        raise CookieAdapterResponseError("The XipuAI backend returned an empty response.")

    if "text/event-stream" in content_type or raw_text.startswith("data:"):
        sse_answer = _parse_sse_text(raw_text)
        if sse_answer:
            return sse_answer

    try:
        data = response.json()
    except json.JSONDecodeError:
        return raw_text

    answer = _extract_known_text(data)
    if not answer:
        raise CookieAdapterResponseError(
            "Could not extract assistant answer from the XipuAI backend response. "
            "Update parse_response_text() for the real response schema."
        )
    return answer


def _build_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": SCHOOL_GPT_BASE_URL,
        "Referer": f"{SCHOOL_GPT_BASE_URL}/v3/chat",
    }

    # Optional token from localStorage. This is useful only when the authorized school endpoint requires it.
    token_key = os.getenv("XIPUAI_AUTH_HEADER_FROM_LOCALSTORAGE", "").strip()
    token_header = os.getenv("XIPUAI_AUTH_HEADER_NAME", "Authorization").strip() or "Authorization"
    token_prefix = os.getenv("XIPUAI_AUTH_HEADER_PREFIX", "Bearer").strip()
    token_value = load_local_storage_value(token_key) if token_key else None

    if token_value:
        headers[token_header] = f"{token_prefix} {token_value}".strip()

    extra_headers_json = os.getenv("XIPUAI_EXTRA_HEADERS_JSON", "").strip()
    if extra_headers_json:
        try:
            extra_headers = json.loads(extra_headers_json)
        except json.JSONDecodeError as exc:
            raise CookieAdapterConfigError("XIPUAI_EXTRA_HEADERS_JSON is not valid JSON.") from exc
        if not isinstance(extra_headers, dict):
            raise CookieAdapterConfigError("XIPUAI_EXTRA_HEADERS_JSON must be a JSON object.")
        for key, value in extra_headers.items():
            headers[str(key)] = str(value)

    return headers


async def ask_school_gpt_by_cookie(question: str, model: str = "auto") -> str:
    """
    Experimental fast adapter that calls an authorized XipuAI backend endpoint with local cookies.

    Required local configuration:
    - school_gpt_state.json generated by xjgpt-login
    - XIPUAI_CHAT_ENDPOINT set to the authorized school backend chat endpoint

    The adapter does not upload, print, or persist cookie values.
    """
    endpoint_url = _build_url(SCHOOL_GPT_CHAT_ENDPOINT)
    cookies = load_cookies_from_storage_state(SCHOOL_GPT_STATE_FILE)
    payload = build_payload(question, model=model)
    headers = _build_headers()
    method = os.getenv("XIPUAI_API_METHOD", "POST").strip().upper()

    async with httpx.AsyncClient(cookies=cookies, timeout=120, follow_redirects=True) as client:
        if method == "POST":
            response = await client.post(endpoint_url, json=payload, headers=headers)
        else:
            response = await client.request(method, endpoint_url, json=payload, headers=headers)

    if response.status_code >= 400:
        safe_body = response.text[:500]
        raise CookieAdapterResponseError(
            f"XipuAI backend request failed with HTTP {response.status_code}. "
            f"Response preview: {safe_body}"
        )

    return parse_response_text(response)

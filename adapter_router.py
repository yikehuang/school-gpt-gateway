import os
from typing import Dict, Any

from school_gpt_adapter import ask_school_gpt as ask_school_gpt_web
from school_gpt_adapter import MODEL_LABELS


SUPPORTED_ADAPTER_MODES = {"web", "cookie", "cookie-http", "http"}


def get_adapter_mode() -> str:
    """Read the active upstream adapter mode from local environment variables."""
    mode = os.getenv("XJGPT_ADAPTER_MODE") or os.getenv("ADAPTER_MODE") or "web"
    return mode.strip().lower()


async def ask_school_gpt(question: str, model: str = "auto") -> str:
    """
    Route a gateway chat request to the selected upstream adapter.

    web:        Playwright controls the authorized XipuAI web page.
    cookie:     HTTP client reads local Playwright storage_state cookies and calls a configured endpoint.

    Cookie mode is experimental and requires XIPUAI_CHAT_ENDPOINT to be configured locally.
    """
    mode = get_adapter_mode()

    if mode == "web":
        return await ask_school_gpt_web(question, model=model)

    if mode in {"cookie", "cookie-http", "http"}:
        from school_gpt_cookie_adapter import ask_school_gpt_by_cookie
        return await ask_school_gpt_by_cookie(question, model=model)

    supported = ", ".join(sorted(SUPPORTED_ADAPTER_MODES))
    raise RuntimeError(f"Unsupported adapter mode: {mode}. Supported modes: {supported}.")


def get_adapter_status() -> Dict[str, Any]:
    """Return safe adapter status without exposing cookie values or secrets."""
    mode = get_adapter_mode()
    endpoint = os.getenv("XIPUAI_CHAT_ENDPOINT", "")

    return {
        "mode": mode,
        "supported_modes": sorted(SUPPORTED_ADAPTER_MODES),
        "cookie_endpoint_configured": bool(endpoint.strip()),
        "state_file": os.getenv("XJGPT_STATE_FILE", "school_gpt_state.json"),
    }

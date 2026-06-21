import asyncio
import json
import re
from pathlib import Path
from typing import Any

import httpx
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 西交利物浦大学 XipuAI 网页版 GPT
SCHOOL_GPT_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"
SCHOOL_GPT_BASE_URL = "https://xipuai.xjtlu.edu.cn"
SCHOOL_GPT_STATE_FILE = Path("school_gpt_state.json")

CHAT_CONFIG_URL = f"{SCHOOL_GPT_BASE_URL}/jmapi/api/chat/config?lang=en&sf_request_type=ajax"
CHAT_SESSION_URL = f"{SCHOOL_GPT_BASE_URL}/jmapi/api/chat/session?lang=en&sf_request_type=ajax"
CHAT_COMPLETIONS_URL = f"{SCHOOL_GPT_BASE_URL}/jmapi/api/chat/completions?sf_request_type=fetch"
CHAT_SAVE_SESSION_URL = f"{SCHOOL_GPT_BASE_URL}/jmapi/api/chat/saveSession?sf_request_type=ajax"

HTTP_TIMEOUT = httpx.Timeout(90.0, connect=20.0, read=90.0)

# 前端和 API 可传入这些 model id。label 必须尽量匹配学校网页下拉框里的文字。
# 如果学校页面里的模型名称和这里不同，只需要改 label，不需要改前端接口。
MODEL_LABELS = {
    "auto": None,
    "gpt-5.4": "GPT-5.4",
    "deepseek-r1": "DeepSeek-R1",
    "deepseek-v3": "DeepSeek-V3",
    "qwen-max": "Qwen-Max",
}

DIRECT_MODEL_CANDIDATES = {
    "gpt-5.4": ["gpt-5.4", "GPT-5.4"],
    "deepseek-r1": ["deepseek-r1", "DeepSeek-R1", "DeepseekR1联网"],
    "deepseek-v3": ["deepseek-v3", "DeepSeek-V3", "DeepSeek-V3.1-W8A8"],
    "qwen-max": ["qwen-max", "Qwen-Max"],
}

# XipuAI 聊天输入框候选选择器。
# 如果学校页面更新，可以运行：playwright codegen https://xipuai.xjtlu.edu.cn/v3/chat
# 然后把录制出的输入框选择器替换或补充到这里。
CHAT_INPUT_SELECTORS = [
    "textarea[placeholder*='发送']",
    "textarea[placeholder*='输入']",
    "textarea[placeholder*='message']",
    "textarea[placeholder*='Message']",
    "textarea",
    "[contenteditable='true']",
    "div[role='textbox']",
    "input[placeholder*='发送']",
    "input[placeholder*='输入']",
]

# 多数 GPT 网页支持普通 Enter 发送，Shift + Enter 换行。
SEND_BY_ENTER = True

# 如果 Enter 不发送，可以把 SEND_BY_ENTER 改成 False，并调整按钮选择器。
SEND_BUTTON_SELECTORS = [
    "button:has-text('发送')",
    "button:has-text('Send')",
    "button[type='submit']",
    "[aria-label*='发送']",
    "[aria-label*='send']",
    "[aria-label*='Send']",
]

# 尝试打开模型选择下拉框的候选选择器。
MODEL_MENU_SELECTORS = [
    "button:has-text('GPT')",
    "button:has-text('DeepSeek')",
    "button:has-text('Qwen')",
    "button:has-text('模型')",
    "button:has-text('Model')",
    "[role='combobox']",
    "[aria-label*='模型']",
    "[aria-label*='model']",
    "[class*='model'] button",
    "[class*='Model'] button",
]

# 常见 AI 回复区域选择器。若读取失败，需要用浏览器开发者工具确认真实 class。
ANSWER_SELECTORS = [
    ".assistant-message",
    ".ai-message",
    ".bot-message",
    ".message.assistant",
    "[class*='assistant']",
    "[class*='answer']",
    "[class*='markdown']",
    "[class*='message']",
    "[class*='chat']",
]


class DirectAdapterError(RuntimeError):
    """Raised when direct XipuAI HTTP access cannot be prepared or parsed."""


class DirectBackendError(RuntimeError):
    """Raised when XipuAI's backend returns a valid error response."""


def get_model_label(model: str | None) -> str | None:
    """把 API 传入的 model id 转为学校网页中显示的模型名称。"""
    model_id = (model or "auto").strip()
    return MODEL_LABELS.get(model_id, model_id)


def _load_storage_state() -> dict[str, Any]:
    if not SCHOOL_GPT_STATE_FILE.exists():
        raise DirectAdapterError("没有找到 school_gpt_state.json，请先运行 login_once.py 保存登录状态。")

    try:
        return json.loads(SCHOOL_GPT_STATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DirectAdapterError("school_gpt_state.json 读取失败，请重新运行 login_once.py。") from exc


def _extract_jm_token(state: dict[str, Any]) -> str:
    for origin in state.get("origins", []):
        if origin.get("origin") != SCHOOL_GPT_BASE_URL:
            continue

        for item in origin.get("localStorage", []):
            value = item.get("value", "")

            match = re.search("token\\xa8\\xa8([^\\xa8]+)\\xa8", value)
            if match:
                return match.group(1)

            try:
                parsed = json.loads(value)
            except Exception:
                parsed = None

            if isinstance(parsed, dict) and parsed.get("token"):
                return str(parsed["token"])

    raise DirectAdapterError("登录状态里没有找到 XipuAI jm-token，请重新运行 login_once.py。")


def _build_direct_cookies(state: dict[str, Any]) -> httpx.Cookies:
    cookies = httpx.Cookies()

    for cookie in state.get("cookies", []):
        domain = cookie.get("domain")
        name = cookie.get("name")
        value = cookie.get("value")

        if not domain or not name or value is None:
            continue

        if "xjtlu.edu.cn" in domain:
            cookies.set(name, value, domain=domain, path=cookie.get("path") or "/")

    return cookies


def _build_direct_headers(token: str, accept: str = "application/json, text/plain, */*") -> dict[str, str]:
    return {
        "accept": accept,
        "content-type": "application/json",
        "origin": SCHOOL_GPT_BASE_URL,
        "referer": SCHOOL_GPT_URL,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148 Safari/537.36"
        ),
        "jm-token": token,
    }


def _build_direct_client(state: dict[str, Any]) -> httpx.AsyncClient:
    token = _extract_jm_token(state)
    return httpx.AsyncClient(
        cookies=_build_direct_cookies(state),
        headers=_build_direct_headers(token),
        timeout=HTTP_TIMEOUT,
        trust_env=False,
    )


def _format_model_option(option: dict[str, Any]) -> dict[str, Any] | None:
    value = str(option.get("value") or "").strip()
    label = str(option.get("label") or value).strip()

    if not value:
        return None

    integral = str(option.get("integral") or "").strip()
    description_parts = []

    if integral:
        description_parts.append(integral)
    else:
        description_parts.append("Free")

    if option.get("online"):
        description_parts.append("Online")

    if option.get("thinking"):
        description_parts.append("Thinking")

    if option.get("multimodal"):
        description_parts.append("Multimodal")

    if option.get("plugin"):
        description_parts.append("Plugin")

    expired = str(option.get("expired") or "").strip()
    if expired:
        description_parts.append(f"Expired: {expired}")

    return {
        "id": value,
        "name": label,
        "description": " · ".join(description_parts),
        "upstream_value": value,
        "upstream_label": label,
        "free": not bool(integral),
        "online": bool(option.get("online")),
        "thinking": bool(option.get("thinking")),
        "multimodal": bool(option.get("multimodal")),
        "plugin": bool(option.get("plugin")),
        "integral": integral,
    }


async def list_school_gpt_models() -> list[dict[str, Any]]:
    """Return all XipuAI models visible to the saved school login state."""
    state = _load_storage_state()

    try:
        async with _build_direct_client(state) as client:
            models = await _get_available_models(client)
    except httpx.HTTPError as exc:
        raise DirectAdapterError("XipuAI 模型列表 HTTP 请求失败。") from exc

    options = []
    seen = set()

    for model in models:
        option = _format_model_option(model)
        if not option or option["id"] in seen:
            continue

        seen.add(option["id"])
        options.append(option)

    return options


def _ensure_backend_success(payload: dict[str, Any], action: str) -> Any:
    if payload.get("code") != 0:
        detail = payload.get("msg") or payload.get("data") or payload
        raise DirectBackendError(f"XipuAI {action} 失败：{detail}")

    return payload.get("data")


async def _get_latest_session(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get(CHAT_SESSION_URL)

    if response.status_code != 200:
        raise DirectAdapterError(f"读取 XipuAI 会话失败，HTTP {response.status_code}。")

    try:
        sessions = _ensure_backend_success(response.json(), "读取会话")
    except json.JSONDecodeError as exc:
        raise DirectAdapterError("XipuAI 会话接口返回了无法解析的 JSON。") from exc

    if not sessions:
        raise DirectAdapterError("XipuAI 没有可用会话，请先在网页里创建一次 New Chat。")

    return sessions[0]


async def _get_available_models(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await client.get(CHAT_CONFIG_URL)

    if response.status_code != 200:
        raise DirectAdapterError(f"读取 XipuAI 模型配置失败，HTTP {response.status_code}。")

    try:
        config = _ensure_backend_success(response.json(), "读取模型配置")
    except json.JSONDecodeError as exc:
        raise DirectAdapterError("XipuAI 模型配置接口返回了无法解析的 JSON。") from exc

    models = config.get("models", []) if isinstance(config, dict) else []
    return [model for model in models if isinstance(model, dict)]


async def _resolve_direct_model(client: httpx.AsyncClient, model: str | None) -> str | None:
    model_id = (model or "auto").strip()

    if model_id == "auto":
        return None

    candidates = DIRECT_MODEL_CANDIDATES.get(model_id, [model_id, get_model_label(model_id) or model_id])
    normalized_candidates = [candidate.lower() for candidate in candidates if candidate]
    models = await _get_available_models(client)

    for option in models:
        value = str(option.get("value") or "")
        label = str(option.get("label") or "")

        if value.lower() in normalized_candidates:
            return value

        if label.lower() in normalized_candidates:
            return value

    for option in models:
        value = str(option.get("value") or "")
        label = str(option.get("label") or "")

        if any(candidate in value.lower() or candidate in label.lower() for candidate in normalized_candidates):
            return value

    available = ", ".join(str(option.get("label") or option.get("value")) for option in models[:12])
    raise DirectBackendError(
        f"XipuAI 当前没有找到模型 {model_id}。可用模型示例：{available}"
    )


def _session_update_payload(session: dict[str, Any], model_value: str) -> dict[str, Any]:
    return {
        "lang": "en",
        "id": session["id"],
        "name": session.get("name") or "New Chat",
        "model": model_value,
        "temperature": session.get("temperature", 0.7),
        "prompt": session.get("prompt") or "",
        "icon": session.get("icon") or "",
        "created": session.get("created") or "",
        "updated": session.get("updated") or "",
        "contextCount": session.get("contextCount", 5),
        "maxToken": session.get("maxToken", 0),
        "presencePenalty": session.get("presencePenalty", 0),
        "frequencyPenalty": session.get("frequencyPenalty", 0),
        "topSort": session.get("topSort", 0),
    }


async def _set_session_model_if_needed(
    client: httpx.AsyncClient,
    session: dict[str, Any],
    model_value: str | None,
) -> None:
    if not model_value or session.get("model") == model_value:
        return

    response = await client.post(CHAT_SAVE_SESSION_URL, json=_session_update_payload(session, model_value))

    if response.status_code != 200:
        raise DirectAdapterError(f"更新 XipuAI 会话模型失败，HTTP {response.status_code}。")

    try:
        _ensure_backend_success(response.json(), "更新会话模型")
    except json.JSONDecodeError as exc:
        raise DirectAdapterError("XipuAI 模型更新接口返回了无法解析的 JSON。") from exc


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "too fast" in message or "10006" in message or "频繁" in message


async def _post_direct_completion(
    client: httpx.AsyncClient,
    question: str,
    session_id: int,
    thinking: str = "minimal",
) -> str:
    payload = {
        "text": question,
        "files": [],
        "online": 0,
        "thinking": thinking,
        "sessionId": session_id,
        "responseId": None,
    }

    headers = dict(client.headers)
    headers.update(_build_direct_headers(str(client.headers["jm-token"]), accept="*/*"))

    chunks: list[str] = []

    async with client.stream("POST", CHAT_COMPLETIONS_URL, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise DirectAdapterError(f"XipuAI 直连聊天失败，HTTP {response.status_code}。")

        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue

            raw_data = line.removeprefix("data:").strip()

            if not raw_data or raw_data == "[DONE]":
                continue

            try:
                event = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            code = event.get("code", 0)
            if code != 0:
                detail = event.get("msg") or event.get("data") or f"code={code}"
                raise DirectBackendError(f"XipuAI 后台返回错误：{detail}")

            if event.get("type") == "string":
                chunks.append(str(event.get("data") or ""))

    answer = "".join(chunks).strip()

    if not answer:
        raise DirectAdapterError("XipuAI 直连接口没有返回文本内容。")

    return answer


async def ask_school_gpt_direct(
    question: str,
    model: str | None = "auto",
    thinking: str = "minimal",
) -> str:
    """
    使用保存下来的学校登录态，直接请求 XipuAI 后台接口。

    该路径只复用用户本人手动登录后保存的 cookie 和 jm-token，不绕过学校认证。
    """
    state = _load_storage_state()

    for attempt in range(3):
        try:
            async with _build_direct_client(state) as client:
                session = await _get_latest_session(client)
                model_value = await _resolve_direct_model(client, model)
                await _set_session_model_if_needed(client, session, model_value)
                return await _post_direct_completion(client, question, int(session["id"]), thinking=thinking)
        except DirectBackendError as exc:
            if _is_rate_limit_error(exc) and attempt < 2:
                await asyncio.sleep(2 + attempt * 3)
                continue
            raise
        except httpx.HTTPError as exc:
            raise DirectAdapterError("XipuAI 直连 HTTP 请求失败。") from exc

    raise DirectBackendError("XipuAI 请求过于频繁，请稍后再试。")


async def _fill_first_available(page, selectors, text: str) -> str:
    """找到第一个可见输入框并输入文本，返回实际使用的选择器。"""
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=5000)
            await locator.fill(text)
            return selector
        except Exception:
            continue

    raise RuntimeError("没有找到 XipuAI 的输入框。请使用 playwright codegen 确认输入框选择器。")


async def _click_first_available(page, selectors) -> str:
    """找到第一个可点击按钮并点击，返回实际使用的选择器。"""
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=3000)
            await locator.click()
            return selector
        except Exception:
            continue

    raise RuntimeError("没有找到可点击按钮。请使用 playwright codegen 确认页面选择器。")


async def _wait_for_chat_ready(page, timeout: int = 45000) -> str:
    """Wait until the XipuAI SPA has rendered a usable chat input."""
    deadline = asyncio.get_running_loop().time() + (timeout / 1000)

    while asyncio.get_running_loop().time() < deadline:
        for selector in CHAT_INPUT_SELECTORS:
            locator = page.locator(selector).first
            try:
                if await locator.is_visible(timeout=500):
                    return selector
            except Exception:
                continue

        await page.wait_for_timeout(500)

    body_preview = ""
    try:
        body_preview = (await page.locator("body").inner_text(timeout=3000)).strip()
    except Exception:
        pass

    if body_preview:
        body_preview = body_preview[:300].replace("\n", " | ")
        raise RuntimeError(
            "XipuAI 页面已打开，但没有找到聊天输入框。"
            f"当前页面文本片段：{body_preview}"
        )

    raise RuntimeError("XipuAI 页面打开后没有渲染聊天界面，请检查登录状态或校园网页是否正常。")


async def _select_native_select(page, label: str) -> bool:
    """如果页面使用原生 select，优先用 select_option。"""
    selectors = [
        "select[name*='model']",
        "select[id*='model']",
        "select[class*='model']",
        "select",
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=1000)
            await locator.select_option(label=label)
            return True
        except Exception:
            try:
                await locator.select_option(value=label)
                return True
            except Exception:
                continue
    return False


async def _select_option_by_text(page, label: str) -> bool:
    """在已经打开的菜单中点击指定模型名称。"""
    option_selectors = [
        f"[role='option']:has-text('{label}')",
        f"li:has-text('{label}')",
        f"button:has-text('{label}')",
        f"div[role='menuitem']:has-text('{label}')",
        f"span:has-text('{label}')",
        f"div:has-text('{label}')",
    ]
    for selector in option_selectors:
        locator = page.locator(selector).last
        try:
            await locator.wait_for(state="visible", timeout=2000)
            await locator.click()
            return True
        except Exception:
            continue
    return False


async def _select_model_if_needed(page, model: str | None) -> str:
    """
    根据 API 传入的 model id 选择学校网页模型。

    model="auto" 时不改学校网页当前模型。
    如果网页结构变化导致无法选择，程序会抛出明确错误，方便用 codegen 修正选择器。
    """
    model_id = (model or "auto").strip()
    label = get_model_label(model_id)

    if not label:
        return "auto"

    if await _select_native_select(page, label):
        return model_id

    menu_opened = False
    for selector in MODEL_MENU_SELECTORS:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=1500)
            await locator.click()
            menu_opened = True
            break
        except Exception:
            continue

    if not menu_opened:
        raise RuntimeError(
            f"没有找到 XipuAI 的模型选择入口，无法切换到 {label}。"
            "请使用 playwright codegen 获取模型下拉框选择器，并更新 MODEL_MENU_SELECTORS。"
        )

    await page.wait_for_timeout(500)

    if await _select_option_by_text(page, label):
        await page.wait_for_timeout(500)
        return model_id

    raise RuntimeError(
        f"已打开模型菜单，但没有找到模型选项：{label}。"
        "请确认学校网页中该模型名称是否存在，或更新 MODEL_LABELS。"
    )


async def _extract_latest_answer(page, question: str) -> str:
    """从候选消息区域中提取最后一段不像用户问题的文本。"""
    candidates = []

    for selector in ANSWER_SELECTORS:
        try:
            texts = await page.locator(selector).all_inner_texts()
            for text in texts:
                cleaned = text.strip()
                if cleaned and cleaned != question and cleaned not in candidates:
                    candidates.append(cleaned)
        except Exception:
            continue

    # 过滤欢迎语、用户原问题、输入提示，尽量保留最后一次 AI 回复。
    filtered = []
    for text in candidates:
        if question in text and len(text) <= len(question) + 20:
            continue
        if "Hello, Welcome" in text:
            continue
        if "欢迎" in text and len(text) < 80:
            continue
        if "Shift" in text and "Enter" in text and len(text) < 80:
            continue
        if "shift" in text and "enter" in text and len(text) < 80:
            continue
        filtered.append(text)

    if filtered:
        return filtered[-1]

    body_text = (await page.locator("body").inner_text()).strip()
    if body_text:
        raise RuntimeError(
            "页面已有文本，但没有识别出 AI 回复区域。请在 school_gpt_adapter.py 中更新 ANSWER_SELECTORS。"
        )

    raise RuntimeError("没有读取到 XipuAI 的回答。")


async def ask_school_gpt_browser(
    question: str,
    model: str | None = "auto",
    thinking: str = "minimal",
) -> str:
    """
    使用学校授权的 XipuAI 网页作为上游服务。

    安全边界：
    - 用户手动登录学校账号并保存本地状态；
    - 程序不绕过学校登录或验证码；
    - 程序不读取他人 Cookie；
    - 日志只记录问题长度、回答长度和模型 id，不保存真实对话原文。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            storage_state="school_gpt_state.json"
        )

        page = await context.new_page()

        try:
            # XipuAI is an SPA and keeps loading/long-polling resources, so
            # waiting for networkidle can hang even after the chat UI is ready.
            await page.goto(SCHOOL_GPT_URL, wait_until="commit", timeout=30000)
            await _wait_for_chat_ready(page)

            await _select_model_if_needed(page, model)
            await _fill_first_available(page, CHAT_INPUT_SELECTORS, question)

            if SEND_BY_ENTER:
                await page.keyboard.press("Enter")
            else:
                await _click_first_available(page, SEND_BUTTON_SELECTORS)

            # 等待页面生成回答。真实页面若有“停止生成”按钮，可以改成等待该按钮消失。
            await page.wait_for_timeout(8000)

            answer = await _extract_latest_answer(page, question)

            if not answer:
                raise RuntimeError("XipuAI 返回了空回答。")

            return answer

        except PlaywrightTimeoutError as exc:
            raise RuntimeError("XipuAI 响应超时。") from exc

        finally:
            await browser.close()


async def ask_school_gpt(
    question: str,
    model: str | None = "auto",
    thinking: str = "minimal",
) -> str:
    try:
        return await ask_school_gpt_direct(question, model=model, thinking=thinking)
    except DirectBackendError:
        raise
    except DirectAdapterError:
        return await ask_school_gpt_browser(question, model=model, thinking=thinking)

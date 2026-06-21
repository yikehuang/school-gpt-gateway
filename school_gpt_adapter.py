import asyncio

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

SCHOOL_GPT_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"

CHAT_INPUT_SELECTORS = [
    "textarea.n-input__textarea-el[placeholder*='Input chat content']",
    "textarea[placeholder*='Input chat content']",
    "textarea[placeholder*='message']",
    "textarea[placeholder*='Message']",
    "textarea",
    "[contenteditable='true']",
    "div[role='textbox']",
]

SEND_BY_ENTER = True

SEND_BUTTON_SELECTORS = [
    "button:has-text('Send')",
    "button[type='submit']",
    "[aria-label*='send']",
    "[aria-label*='Send']",
]

NEW_CHAT_BUTTON_SELECTORS = [
    "button.n-button--medium-type.bg-gradient-to-br",
]

ANSWER_SELECTORS = [
    ".xp-chat-content",
    ".bg-white .xp-chat-content",
    ".bg-white.rounded-b-xl.rounded-tr-xl",
    ".assistant-message",
    ".ai-message",
    ".bot-message",
    ".message.assistant",
    "[class*='assistant']",
    "[class*='answer']",
    "[class*='markdown']",
]

GENERATING_TEXT_MARKERS = (
    "thinking",
    "thinking...",
    "thinking…",
    "loading",
    "generating",
)

_BROWSER_LOCK = asyncio.Lock()
_PLAYWRIGHT = None
_BROWSER = None
_CONTEXT = None
_PAGE = None


async def _launch_chromium(playwright, *, headless: bool):
    last_error = None

    for channel in ("msedge", "chrome", None):
        options = {"headless": headless}
        if channel:
            options["channel"] = channel

        try:
            return await playwright.chromium.launch(**options)
        except Exception as exc:
            last_error = exc

    raise RuntimeError("No Chromium-compatible browser could be launched.") from last_error


async def _reset_browser() -> None:
    global _PLAYWRIGHT, _BROWSER, _CONTEXT, _PAGE

    for resource in (_PAGE, _CONTEXT, _BROWSER):
        if resource is not None:
            try:
                await resource.close()
            except Exception:
                pass

    if _PLAYWRIGHT is not None:
        try:
            await _PLAYWRIGHT.stop()
        except Exception:
            pass

    _PLAYWRIGHT = None
    _BROWSER = None
    _CONTEXT = None
    _PAGE = None


async def _get_page():
    global _PLAYWRIGHT, _BROWSER, _CONTEXT, _PAGE

    if _PAGE is not None and not _PAGE.is_closed():
        return _PAGE

    _PLAYWRIGHT = await async_playwright().start()
    _BROWSER = await _launch_chromium(_PLAYWRIGHT, headless=True)
    _CONTEXT = await _BROWSER.new_context(storage_state="school_gpt_state.json")
    _PAGE = await _CONTEXT.new_page()
    return _PAGE


async def _fill_first_available(page, selectors, text: str) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=5000)
            await locator.fill(text)
            return selector
        except Exception:
            continue

    raise RuntimeError("Could not find the XipuAI chat input.")


async def _click_first_available(page, selectors) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=3000)
            await locator.click()
            return selector
        except Exception:
            continue

    raise RuntimeError("Could not find the XipuAI send button.")


async def _start_new_chat(page) -> None:
    for selector in NEW_CHAT_BUTTON_SELECTORS:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=5000)
            await locator.click()
            await page.wait_for_timeout(2000)
            return
        except Exception:
            continue


def _clean_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()


def _squash_text(text: str) -> str:
    return " ".join(text.split())


def _looks_like_non_answer(text: str, question: str) -> bool:
    if not text or text == question:
        return True

    squashed_text = _squash_text(text)
    squashed_question = _squash_text(question)
    if squashed_question and squashed_question in squashed_text:
        tail = squashed_text[squashed_text.rfind(squashed_question) + len(squashed_question):].strip()
        if len(tail) < 8:
            return True

    normalized = text.strip().lower()
    if normalized in GENERATING_TEXT_MARKERS:
        return True
    if any(marker in normalized for marker in GENERATING_TEXT_MARKERS):
        if len(normalized) <= 80:
            return True

    if "hello, welcome" in normalized:
        return True
    if "hello, i am your ai assistant" in normalized:
        return True
    if "shift" in normalized and "enter" in normalized and len(text) < 120:
        return True

    return False


async def _collect_answer_candidates(page, question: str):
    candidates = []

    for selector in ANSWER_SELECTORS:
        try:
            texts = await page.locator(selector).all_inner_texts()
            for text in texts:
                cleaned = _clean_text(text)
                if cleaned and cleaned not in candidates:
                    candidates.append(cleaned)
        except Exception:
            continue

    return candidates


async def _extract_latest_answer(page, question: str, previous_candidates=None) -> str:
    previous = set(previous_candidates or [])

    for _ in range(30):
        candidates = await _collect_answer_candidates(page, question)
        filtered = [
            text
            for text in candidates
            if text not in previous and not _looks_like_non_answer(text, question)
        ]

        if filtered:
            return filtered[-1]

        await page.wait_for_timeout(2000)

    body_text = (await page.locator("body").inner_text()).strip()
    if body_text:
        raise RuntimeError("No new XipuAI answer was detected. Update ANSWER_SELECTORS if the page changed.")

    raise RuntimeError("No XipuAI answer text was found.")


async def ask_school_gpt(question: str) -> str:
    async with _BROWSER_LOCK:
        try:
            page = await _get_page()
            await page.goto(SCHOOL_GPT_URL, wait_until="domcontentloaded", timeout=60000)
            await _start_new_chat(page)

            previous_candidates = await _collect_answer_candidates(page, question)

            await _fill_first_available(page, CHAT_INPUT_SELECTORS, question)

            if SEND_BY_ENTER:
                await page.keyboard.press("Enter")
            else:
                await _click_first_available(page, SEND_BUTTON_SELECTORS)

            answer = await _extract_latest_answer(page, question, previous_candidates)

            if not answer:
                raise RuntimeError("XipuAI returned an empty answer.")

            return answer

        except PlaywrightTimeoutError as exc:
            await _reset_browser()
            raise RuntimeError("XipuAI timed out.") from exc
        except Exception:
            if _PAGE is not None and _PAGE.is_closed():
                await _reset_browser()
            raise

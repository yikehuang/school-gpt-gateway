from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 西交利物浦大学 XipuAI 网页版 GPT
SCHOOL_GPT_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"

# 前端和 API 可传入这些 model id。label 必须尽量匹配学校网页下拉框里的文字。
# 如果学校页面里的模型名称和这里不同，只需要改 label，不需要改前端接口。
MODEL_LABELS = {
    "auto": None,
    "gpt-5.4": "GPT-5.4",
    "deepseek-r1": "DeepSeek-R1",
    "deepseek-v3": "DeepSeek-V3",
    "qwen-max": "Qwen-Max",
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


def get_model_label(model: str | None) -> str | None:
    """把 API 传入的 model id 转为学校网页中显示的模型名称。"""
    model_id = (model or "auto").strip()
    return MODEL_LABELS.get(model_id, model_id)


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


async def ask_school_gpt(question: str, model: str | None = "auto") -> str:
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
            await page.goto(SCHOOL_GPT_URL, wait_until="networkidle", timeout=60000)

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

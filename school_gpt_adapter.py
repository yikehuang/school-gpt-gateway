from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 西交利物浦大学 Ehall AI 页面
SCHOOL_GPT_URL = "https://ehall.xjtlu.edu.cn/default/index.html#/wiseQA"

# 根据当前截图，输入框大概率是 textarea，并带有“发送消息”占位文字。
# 如果学校页面更新，可以运行：playwright codegen https://ehall.xjtlu.edu.cn/default/index.html#/wiseQA
# 然后把录制出的输入框选择器替换到这里。
CHAT_INPUT_SELECTORS = [
    "textarea[placeholder*='发送消息']",
    "textarea[placeholder*='shift']",
    "textarea",
    "[contenteditable='true']",
    "div[role='textbox']",
]

# Ehall AI 的输入框提示为“shift + enter 换行”，所以普通 Enter 通常用于发送。
# 这里优先用 Enter 发送，避免误点页面右侧或顶部的其他按钮。
SEND_BY_ENTER = True

# 常见 AI 回复区域选择器。若读取失败，需要用浏览器开发者工具确认真实 class。
ANSWER_SELECTORS = [
    ".assistant-message",
    ".ai-message",
    ".bot-message",
    ".message.assistant",
    "[class*='assistant']",
    "[class*='answer']",
    "[class*='message']",
    "[class*='chat']",
]


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

    raise RuntimeError("没有找到 Ehall AI 的输入框。请使用 playwright codegen 确认输入框选择器。")


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

    # 过滤欢迎语和用户原问题，尽量保留最后一次 AI 回复。
    filtered = []
    for text in candidates:
        if question in text and len(text) <= len(question) + 20:
            continue
        if "Hello, Welcome to inquire" in text:
            continue
        if "你好！欢迎咨询XJTLU" in text:
            continue
        filtered.append(text)

    if filtered:
        return filtered[-1]

    # 兜底：读取页面正文，便于调试，但避免直接返回整页侧边栏内容。
    body_text = (await page.locator("body").inner_text()).strip()
    if body_text:
        raise RuntimeError(
            "页面已有文本，但没有识别出 AI 回复区域。请在 school_gpt_adapter.py 中更新 ANSWER_SELECTORS。"
        )

    raise RuntimeError("没有读取到 Ehall AI 的回答。")


async def ask_school_gpt(question: str) -> str:
    """
    使用学校授权的 Ehall AI 网页作为上游服务。

    安全边界：
    - 用户手动登录学校账号并保存本地状态；
    - 程序不绕过学校登录或验证码；
    - 程序不读取他人 Cookie；
    - 日志只记录问题长度和回答长度，不保存真实对话原文。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            storage_state="school_gpt_state.json"
        )

        page = await context.new_page()

        try:
            await page.goto(SCHOOL_GPT_URL, wait_until="networkidle", timeout=60000)

            await _fill_first_available(page, CHAT_INPUT_SELECTORS, question)

            if SEND_BY_ENTER:
                await page.keyboard.press("Enter")
            else:
                await page.click("button:has-text('发送')")

            # 等待页面生成回答。真实页面若有“停止生成”按钮，可以改成等待该按钮消失。
            await page.wait_for_timeout(8000)

            answer = await _extract_latest_answer(page, question)

            if not answer:
                raise RuntimeError("Ehall AI 返回了空回答。")

            return answer

        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Ehall AI 响应超时。") from exc

        finally:
            await browser.close()

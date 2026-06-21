from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# TODO: 改成学校网页版 GPT 的真实地址
SCHOOL_GPT_URL = "https://your-school-gpt-url.example.com"

# TODO: 根据学校 GPT 页面实际元素修改这些选择器
CHAT_INPUT_SELECTOR = "textarea"
SEND_BUTTON_SELECTOR = "button[type='submit']"
ANSWER_SELECTOR = ".assistant-message"


async def ask_school_gpt(question: str) -> str:
    """
    使用学校授权的网页版 GPT 作为上游服务。

    安全边界：
    - 不绕过学校登录；
    - 不破解验证码；
    - 不读取他人 Cookie；
    - 不保存用户敏感对话原文。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            storage_state="school_gpt_state.json"
        )

        page = await context.new_page()

        try:
            await page.goto(SCHOOL_GPT_URL, wait_until="networkidle", timeout=60000)

            await page.fill(CHAT_INPUT_SELECTOR, question)
            await page.click(SEND_BUTTON_SELECTOR)

            await page.wait_for_selector(ANSWER_SELECTOR, timeout=60000)

            # 简化处理：等待生成完成。正式版本可以改成监听“停止生成”按钮消失。
            await page.wait_for_timeout(3000)

            answers = await page.locator(ANSWER_SELECTOR).all_inner_texts()

            if not answers:
                raise RuntimeError("没有读取到学校 GPT 的回答。")

            latest_answer = answers[-1].strip()

            if not latest_answer:
                raise RuntimeError("学校 GPT 返回了空回答。")

            return latest_answer

        except PlaywrightTimeoutError as exc:
            raise RuntimeError("学校 GPT 响应超时。") from exc

        finally:
            await browser.close()

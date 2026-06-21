from playwright.sync_api import sync_playwright

SCHOOL_GPT_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"


def launch_chromium(playwright, *, headless: bool):
    last_error = None

    for channel in ("msedge", "chrome", None):
        options = {"headless": headless}
        if channel:
            options["channel"] = channel

        try:
            return playwright.chromium.launch(**options)
        except Exception as exc:
            last_error = exc

    raise RuntimeError("No Chromium-compatible browser could be launched.") from last_error


def main():
    with sync_playwright() as p:
        browser = launch_chromium(p, headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(SCHOOL_GPT_URL, wait_until="networkidle")

        print("Log in to XipuAI in the browser window.")
        print("After the chat page is visible, return here and press Enter.")
        input()

        context.storage_state(path="school_gpt_state.json")
        print("Login state saved to school_gpt_state.json")
        print("Do not upload school_gpt_state.json to GitHub.")

        browser.close()


if __name__ == "__main__":
    main()

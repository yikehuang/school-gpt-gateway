from playwright.sync_api import sync_playwright

# 西交利物浦大学 XipuAI 网页版 GPT
SCHOOL_GPT_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # The XipuAI single-page app may keep background requests open, so
        # wait only until navigation has committed before the user logs in.
        page.goto(SCHOOL_GPT_URL, wait_until="commit")

        print("请在打开的浏览器中手动登录学校 XipuAI。")
        print("登录完成并看到 XipuAI 聊天页面后，回到终端按 Enter。")
        input()

        context.storage_state(path="school_gpt_state.json")
        print("登录状态已保存到 school_gpt_state.json")
        print("注意：不要把 school_gpt_state.json 上传到 GitHub。")

        browser.close()


if __name__ == "__main__":
    main()

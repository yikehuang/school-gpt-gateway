from playwright.sync_api import sync_playwright

# 西交利物浦大学 Ehall AI 页面
SCHOOL_GPT_URL = "https://ehall.xjtlu.edu.cn/default/index.html#/wiseQA"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(SCHOOL_GPT_URL, wait_until="networkidle")

        print("请在打开的浏览器中手动登录学校 Ehall AI。")
        print("登录完成并看到 Ehall AI 聊天页面后，回到终端按 Enter。")
        input()

        context.storage_state(path="school_gpt_state.json")
        print("登录状态已保存到 school_gpt_state.json")
        print("注意：不要把 school_gpt_state.json 上传到 GitHub。")

        browser.close()


if __name__ == "__main__":
    main()

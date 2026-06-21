"""
Cookie/local login-state tester for XJGPT School Gateway.

This script is intended to run on the user's own computer after `xjgpt-login`
or `python login_once.py` has generated `school_gpt_state.json` locally.

It does not print cookie values. It only prints cookie names and basic validity
checks so that login credentials are not exposed in terminal screenshots.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright

DEFAULT_STATE_PATH = "school_gpt_state.json"
DEFAULT_PAGE_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"
DEFAULT_DOMAIN_HINTS = ("xipuai.xjtlu.edu.cn", ".xjtlu.edu.cn", "xjtlu.edu.cn")
LOGIN_KEYWORDS = (
    "login",
    "sign in",
    "sso",
    "统一身份认证",
    "登录",
    "用户名",
    "password",
    "cas",
)
CHAT_KEYWORDS = (
    "chat",
    "new chat",
    "发送",
    "模型",
    "xipuai",
    "assistant",
    "问我任何问题",
)


def load_storage_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot find {path}. Run `xjgpt-login` or `python login_once.py` first."
        )

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def matching_cookies(state: Dict[str, Any], domain_hints: List[str]) -> List[Dict[str, Any]]:
    cookies = state.get("cookies", [])
    results = []

    for cookie in cookies:
        domain = cookie.get("domain", "") or ""
        if any(hint in domain for hint in domain_hints):
            results.append(cookie)

    return results


def print_cookie_summary(cookies: List[Dict[str, Any]]) -> None:
    if not cookies:
        print("[FAIL] No XJTLU/XipuAI cookies found in storage state.")
        return

    print(f"[OK] Found {len(cookies)} related cookie(s). Values are hidden.")
    for cookie in cookies:
        name = cookie.get("name", "<unknown>")
        domain = cookie.get("domain", "<unknown>")
        expires = cookie.get("expires", -1)
        http_only = cookie.get("httpOnly", False)
        secure = cookie.get("secure", False)
        print(
            f"  - name={name}, domain={domain}, expires={expires}, "
            f"httpOnly={http_only}, secure={secure}"
        )


def looks_like_login(text: str, final_url: str) -> bool:
    lower_text = text.lower()
    lower_url = final_url.lower()
    return any(keyword.lower() in lower_text or keyword.lower() in lower_url for keyword in LOGIN_KEYWORDS)


def looks_like_chat(text: str, final_url: str) -> bool:
    lower_text = text.lower()
    lower_url = final_url.lower()
    return any(keyword.lower() in lower_text or keyword.lower() in lower_url for keyword in CHAT_KEYWORDS)


async def test_page_with_playwright(state_path: Path, page_url: str, headless: bool) -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(storage_state=str(state_path))
        page = await context.new_page()

        try:
            response = await page.goto(page_url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2500)
            final_url = page.url
            title = await page.title()
            body_text = await page.locator("body").inner_text(timeout=10000)

            print("\n[PAGE TEST]")
            print(f"Target URL: {page_url}")
            print(f"Final URL:  {final_url}")
            print(f"Title:      {title}")
            print(f"HTTP:       {response.status if response else 'unknown'}")

            snippet = " ".join(body_text.split())[:300]
            print(f"Body head:  {snippet}")

            if looks_like_login(body_text, final_url):
                print("[FAIL] The saved cookie/state probably cannot enter XipuAI. It looks like a login page.")
                return 2

            if looks_like_chat(body_text, final_url):
                print("[OK] The saved cookie/state appears usable for the XipuAI web page.")
                return 0

            print("[WARN] The page loaded, but the script cannot confidently identify chat UI or login UI.")
            print("       Open the browser with `--show-browser` and verify manually.")
            return 1

        finally:
            await browser.close()


async def test_optional_api(
    state_path: Path,
    endpoint: str,
    method: str,
    payload_path: Optional[Path],
) -> int:
    async with async_playwright() as p:
        request_context = await p.request.new_context(storage_state=str(state_path))

        headers = {
            "Content-Type": "application/json",
            "Origin": "https://xipuai.xjtlu.edu.cn",
            "Referer": DEFAULT_PAGE_URL,
        }

        data = None
        if payload_path:
            with payload_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

        print("\n[OPTIONAL API TEST]")
        print(f"Endpoint: {endpoint}")
        print(f"Method:   {method.upper()}")

        try:
            if method.lower() == "get":
                response = await request_context.get(endpoint, headers=headers, timeout=60000)
            elif method.lower() == "post":
                response = await request_context.post(endpoint, headers=headers, data=data, timeout=60000)
            else:
                raise ValueError("method must be GET or POST")

            text = await response.text()
            print(f"HTTP:     {response.status}")
            print(f"Preview:  {' '.join(text.split())[:500]}")

            if response.status in (401, 403):
                print("[FAIL] Cookie/state reached the endpoint but was not authorised.")
                return 2

            if response.status >= 400:
                print("[WARN] Endpoint returned an error. The endpoint path or payload may be wrong.")
                return 1

            print("[OK] Cookie/state can call this endpoint. Check preview to confirm response format.")
            return 0

        finally:
            await request_context.dispose()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Test local XipuAI cookies/storage state.")
    parser.add_argument("--state", default=DEFAULT_STATE_PATH, help="Path to school_gpt_state.json")
    parser.add_argument("--page-url", default=DEFAULT_PAGE_URL, help="XipuAI page URL to test")
    parser.add_argument("--show-browser", action="store_true", help="Open visible browser for manual checking")
    parser.add_argument(
        "--domain-hint",
        action="append",
        default=None,
        help="Cookie domain substring to include. Can be provided multiple times.",
    )
    parser.add_argument("--api-endpoint", default=None, help="Optional real XipuAI backend endpoint to test")
    parser.add_argument("--api-method", default="POST", choices=["GET", "POST", "get", "post"])
    parser.add_argument("--payload", default=None, help="Optional JSON payload file for API POST test")

    args = parser.parse_args()
    state_path = Path(args.state)
    payload_path = Path(args.payload) if args.payload else None
    domain_hints = args.domain_hint or list(DEFAULT_DOMAIN_HINTS)

    state = load_storage_state(state_path)
    cookies = matching_cookies(state, domain_hints)

    print("[COOKIE SUMMARY]")
    print(f"State file: {state_path}")
    print_cookie_summary(cookies)

    if not cookies:
        return 2

    page_code = await test_page_with_playwright(
        state_path=state_path,
        page_url=args.page_url,
        headless=not args.show_browser,
    )

    if args.api_endpoint:
        api_code = await test_optional_api(
            state_path=state_path,
            endpoint=args.api_endpoint,
            method=args.api_method,
            payload_path=payload_path,
        )
        return max(page_code, api_code)

    print("\n[NOTE]")
    print("This test proves whether the saved cookie/state can enter the XipuAI web page.")
    print("To test direct HTTP API access, provide the real backend endpoint with --api-endpoint.")
    return page_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

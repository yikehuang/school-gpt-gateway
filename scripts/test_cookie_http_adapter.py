import argparse
import asyncio
import os
from pathlib import Path

from school_gpt_cookie_adapter import (
    SCHOOL_GPT_CHAT_ENDPOINT,
    SCHOOL_GPT_STATE_FILE,
    ask_school_gpt_by_cookie,
    load_cookies_from_storage_state,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Test the experimental XipuAI cookie HTTP adapter locally.")
    parser.add_argument("--question", default="请只回复两个字：成功", help="Question to send to XipuAI.")
    parser.add_argument("--model", default="auto", help="Model id to send, such as auto or gpt-5.4.")
    parser.add_argument("--check-cookies-only", action="store_true", help="Only check whether local cookies exist.")
    return parser.parse_args()


async def main():
    args = parse_args()

    print("[XJGPT] Cookie HTTP adapter local test")
    print(f"[INFO] State file: {SCHOOL_GPT_STATE_FILE}")
    print(f"[INFO] Endpoint configured: {bool(SCHOOL_GPT_CHAT_ENDPOINT.strip())}")

    if not Path(SCHOOL_GPT_STATE_FILE).exists():
        print("[ERROR] school_gpt_state.json not found. Run xjgpt-login first.")
        return

    try:
        cookies = load_cookies_from_storage_state(SCHOOL_GPT_STATE_FILE)
    except Exception as exc:
        print(f"[ERROR] Cookie check failed: {exc}")
        return

    print(f"[OK] Found {len(cookies)} XipuAI/XJTLU related cookie(s). Values are hidden.")
    print("[INFO] Cookie names:")
    for name in sorted(cookies.keys()):
        print(f"  - {name}")

    if args.check_cookies_only:
        return

    if not SCHOOL_GPT_CHAT_ENDPOINT.strip():
        print("[ERROR] XIPUAI_CHAT_ENDPOINT is not configured.")
        print("[NEXT] Set the authorized XipuAI backend endpoint locally, then run this script again.")
        return

    try:
        answer = await ask_school_gpt_by_cookie(args.question, model=args.model)
    except Exception as exc:
        print(f"[ERROR] Request failed: {exc}")
        return

    print("[OK] Cookie HTTP adapter returned an answer:")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())

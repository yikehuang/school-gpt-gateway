import argparse
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

DEFAULT_CHAT_URL = "https://xipuai.xjtlu.edu.cn/v3/chat"
DEFAULT_STATE_FILE = "school_gpt_state.json"
DEFAULT_OUTPUT = "local_discovery/xipuai_endpoint_candidates.json"
DEFAULT_ENV_OUTPUT = ".env.cookie.local"

INPUT_SELECTORS = [
    "textarea[placeholder*='发送']",
    "textarea[placeholder*='输入']",
    "textarea[placeholder*='message' i]",
    "textarea",
    "[contenteditable='true']",
    "div[role='textbox']",
    "input[type='text']",
]

SEND_BUTTON_SELECTORS = [
    "button:has-text('发送')",
    "button:has-text('Send')",
    "button[type='submit']",
    "[aria-label*='发送']",
    "[aria-label*='Send' i]",
]

SENSITIVE_HEADER_NAMES = {
    "cookie",
    "authorization",
    "proxy-authorization",
    "x-csrf-token",
    "x-xsrf-token",
    "csrf-token",
    "set-cookie",
}

CHAT_KEYWORDS = (
    "chat",
    "completion",
    "conversation",
    "message",
    "ask",
    "qa",
    "stream",
    "bot",
    "agent",
)

PAYLOAD_KEYS = (
    "messages",
    "message",
    "question",
    "prompt",
    "content",
    "input",
    "model",
)


class RequestRecord:
    def __init__(self, request_id: int, request: Any):
        self.id = request_id
        self.method = request.method
        self.url = request.url
        self.resource_type = request.resource_type
        self.post_data = request.post_data or ""
        self.headers = request.headers or {}
        self.started_at = time.time()
        self.status: Optional[int] = None
        self.response_content_type = ""
        self.response_preview = ""
        self.finished_at: Optional[float] = None

    def payload_shape(self) -> Dict[str, Any]:
        if not self.post_data:
            return {"type": "empty"}

        text = self.post_data.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {
                "type": "text",
                "length": len(text),
                "preview": _compact_text(_redact_value(text), 200),
            }

        return _describe_json_shape(data)

    def infer_payload_style(self) -> str:
        if not self.post_data:
            return "unknown"
        try:
            data = json.loads(self.post_data)
        except json.JSONDecodeError:
            return "unknown"
        if isinstance(data, dict):
            if isinstance(data.get("messages"), list):
                return "openai"
            if any(key in data for key in ("question", "prompt", "input")):
                return "simple"
        return "unknown"

    def score(self, expected_answer: str = "") -> int:
        score = 0
        lower_url = self.url.lower()
        lower_post = self.post_data.lower()
        lower_preview = self.response_preview.lower()
        content_type = self.response_content_type.lower()

        if self.method.upper() == "POST":
            score += 35
        if self.resource_type in {"xhr", "fetch", "eventsource", "websocket"}:
            score += 15
        if any(keyword in lower_url for keyword in CHAT_KEYWORDS):
            score += 25
        if any(key in lower_post for key in PAYLOAD_KEYS):
            score += 25
        if "json" in content_type or "event-stream" in content_type or "stream" in content_type:
            score += 15
        if self.status and 200 <= self.status < 300:
            score += 20
        if expected_answer and expected_answer.lower() in lower_preview:
            score += 30
        if self.status in {401, 403}:
            score -= 10
        if any(token in lower_url for token in ("login", "captcha", "logout", "static", "asset")):
            score -= 30
        return score

    def safe_dict(self, expected_answer: str = "") -> Dict[str, Any]:
        parsed = urlparse(self.url)
        header_names = sorted(self.headers.keys())
        non_sensitive_headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in SENSITIVE_HEADER_NAMES and not _looks_sensitive_header(key)
        }
        return {
            "id": self.id,
            "score": self.score(expected_answer=expected_answer),
            "method": self.method,
            "url": self.url,
            "same_origin_path": parsed.path + (f"?{parsed.query}" if parsed.query else ""),
            "resource_type": self.resource_type,
            "status": self.status,
            "response_content_type": self.response_content_type,
            "payload_style_guess": self.infer_payload_style(),
            "payload_shape": self.payload_shape(),
            "header_names": header_names,
            "non_sensitive_headers": non_sensitive_headers,
            "response_preview": _compact_text(_redact_value(self.response_preview), 500),
        }


def _looks_sensitive_header(name: str) -> bool:
    lower = name.lower()
    return any(token in lower for token in ("token", "secret", "session", "jwt", "auth", "cookie"))


def _redact_value(text: str) -> str:
    patterns = [
        r"Bearer\s+[A-Za-z0-9._\-]+",
        r"(?i)(token|access_token|refresh_token|id_token|session|secret|password)\s*[:=]\s*['\"]?[^,'\"\s}]+",
        r"(?i)(cookie)\s*[:=]\s*[^\n]+",
    ]
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, r"\1=<REDACTED>", redacted)
    return redacted


def _compact_text(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _describe_json_shape(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        result: Dict[str, Any] = {"type": "object", "keys": sorted(map(str, data.keys()))}
        sample: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                sample[str(key)] = {"type": "string", "length": len(value)}
            elif isinstance(value, list):
                sample[str(key)] = {"type": "list", "length": len(value)}
            elif isinstance(value, dict):
                sample[str(key)] = {"type": "object", "keys": sorted(map(str, value.keys()))[:20]}
            else:
                sample[str(key)] = {"type": type(value).__name__}
        result["fields"] = sample
        return result
    if isinstance(data, list):
        return {"type": "list", "length": len(data), "first_item": _describe_json_shape(data[0]) if data else None}
    return {"type": type(data).__name__}


def _endpoint_value(url: str, base_url: str) -> str:
    parsed = urlparse(url)
    base = urlparse(base_url)
    if parsed.scheme == base.scheme and parsed.netloc == base.netloc:
        return parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return url


def _write_report(records: List[RequestRecord], output: str, base_url: str, expected_answer: str) -> Dict[str, Any]:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    candidates = sorted(
        [record.safe_dict(expected_answer=expected_answer) for record in records],
        key=lambda item: item["score"],
        reverse=True,
    )

    best = candidates[0] if candidates else None
    report = {
        "generated_at": int(time.time()),
        "base_url": base_url,
        "note": "Sensitive header values and cookie values are not included. Keep this file local.",
        "best_candidate": best,
        "candidates": candidates[:25],
    }

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _write_env_hint(report: Dict[str, Any], env_output: str, base_url: str) -> None:
    best = report.get("best_candidate")
    if not best:
        return

    endpoint = _endpoint_value(best["url"], base_url)
    payload_style = best.get("payload_style_guess") or "openai"
    if payload_style == "unknown":
        payload_style = "openai"

    env_text = "\n".join(
        [
            "# Local cookie adapter configuration generated by xjgpt-discover-endpoint.",
            "# Review these values before use. Do not commit this file.",
            "XJGPT_ADAPTER_MODE=cookie",
            f"XIPUAI_CHAT_ENDPOINT={endpoint}",
            f"XIPUAI_API_METHOD={best.get('method', 'POST')}",
            f"XIPUAI_PAYLOAD_STYLE={payload_style}",
            "",
        ]
    )
    Path(env_output).write_text(env_text, encoding="utf-8")


async def _try_auto_send(page: Any, question: str) -> bool:
    for selector in INPUT_SELECTORS:
        locator = page.locator(selector).first
        try:
            if await locator.count() == 0:
                continue
            await locator.click(timeout=3000)
            await locator.fill(question, timeout=3000)
            await page.keyboard.press("Enter")
            return True
        except Exception:
            continue

    for selector in SEND_BUTTON_SELECTORS:
        try:
            button = page.locator(selector).first
            if await button.count() > 0:
                await button.click(timeout=3000)
                return True
        except Exception:
            continue

    return False


async def discover_endpoint(args: argparse.Namespace) -> None:
    state_path = Path(args.state_file)
    if not state_path.exists():
        print(f"[ERROR] State file not found: {state_path}")
        print("[NEXT] Run xjgpt-login first and log in to XipuAI.")
        return

    records: List[RequestRecord] = []
    request_map: Dict[Any, RequestRecord] = {}
    expected_answer = args.expected_answer.strip()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(storage_state=str(state_path))
        page = await context.new_page()

        def on_request(request: Any) -> None:
            try:
                request_id = len(records) + 1
                record = RequestRecord(request_id, request)
                request_map[request] = record
                records.append(record)
            except Exception:
                return

        async def on_response(response: Any) -> None:
            try:
                request = response.request
                record = request_map.get(request)
                if not record:
                    return
                record.status = response.status
                record.response_content_type = response.headers.get("content-type", "")
                record.finished_at = time.time()

                if record.resource_type in {"xhr", "fetch", "eventsource"} or record.method.upper() == "POST":
                    try:
                        text = await response.text()
                        record.response_preview = text[:2000]
                    except Exception:
                        record.response_preview = ""
            except Exception:
                return

        page.on("request", on_request)
        page.on("response", lambda response: asyncio.create_task(on_response(response)))

        print(f"[XJGPT] Opening {args.url}")
        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)

        if args.manual:
            print("[MANUAL] Ask the test question in the opened browser window.")
            print(f"[QUESTION] {args.question}")
            print(f"[INFO] Capturing network traffic for {args.timeout} seconds...")
        else:
            print("[AUTO] Trying to submit the test question automatically.")
            submitted = await _try_auto_send(page, args.question)
            if submitted:
                print("[OK] Test question submitted. Capturing network traffic...")
            else:
                print("[WARN] Could not auto-submit. Please ask the test question manually in the browser.")

        await page.wait_for_timeout(args.timeout * 1000)
        await browser.close()

    parsed_base = urlparse(args.url)
    base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
    report = _write_report(records, args.output, base_url, expected_answer=expected_answer)
    _write_env_hint(report, args.env_output, base_url)

    best = report.get("best_candidate")
    print(f"[OK] Discovery report written to: {args.output}")
    print(f"[OK] Env hint written to: {args.env_output}")

    if best:
        print("[BEST CANDIDATE]")
        print(f"  score: {best['score']}")
        print(f"  method: {best['method']}")
        print(f"  endpoint: {_endpoint_value(best['url'], base_url)}")
        print(f"  payload style guess: {best['payload_style_guess']}")
        print(f"  status: {best['status']}")
        print("[NEXT] Review .env.cookie.local, then set the variables in your terminal and run scripts/test_cookie_http_adapter.py.")
    else:
        print("[WARN] No candidate requests were captured. Run again with --manual and ask a question in the browser.")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover the authorized XipuAI chat backend endpoint from local Playwright network traffic."
    )
    parser.add_argument("--url", default=DEFAULT_CHAT_URL, help="XipuAI chat page URL.")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="Playwright storage_state file generated by xjgpt-login.")
    parser.add_argument("--question", default="请只回复两个字：成功", help="Test question to send during discovery.")
    parser.add_argument("--expected-answer", default="成功", help="Expected short answer used only for ranking candidates.")
    parser.add_argument("--timeout", type=int, default=45, help="Seconds to capture network traffic after opening the page.")
    parser.add_argument("--manual", action="store_true", help="Do not auto-submit. You ask the question manually in the browser.")
    parser.add_argument("--headless", action="store_true", help="Run Chromium headless. Visible mode is recommended for first use.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Local JSON report path. This file should not be committed.")
    parser.add_argument("--env-output", default=DEFAULT_ENV_OUTPUT, help="Local env hint path. This file should not be committed.")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(discover_endpoint(args))
    except PlaywrightTimeoutError as exc:
        print(f"[ERROR] Playwright timeout: {exc}")
    except KeyboardInterrupt:
        print("\n[INFO] Discovery interrupted by user.")


if __name__ == "__main__":
    main()

# XipuAI Endpoint Discovery

This guide explains the local helper that identifies the XipuAI backend request used by the web page. It is intended for the `feature/cookie-http-adapter` branch.

## Purpose

The cookie HTTP adapter needs the backend chat endpoint before it can call XipuAI directly. The discovery helper opens the authorized XipuAI web page with your locally saved Playwright login state, records local network traffic, ranks likely chat requests, and writes a local report.

The helper does not upload your cookies or token values. It redacts sensitive header values and writes results only to your local machine.

## Run Discovery

First save your XipuAI login state:

```bash
xjgpt-login
```

Then run:

```bash
xjgpt-discover-endpoint
```

The browser opens XipuAI. The helper tries to ask this test question automatically:

```text
请只回复两个字：成功
```

If the page layout prevents automatic submission, run manual mode:

```bash
xjgpt-discover-endpoint --manual --timeout 60
```

In manual mode, ask the test question yourself in the opened browser window. The helper captures the network traffic while you do this.

## Output Files

The helper writes two local files:

```text
local_discovery/xipuai_endpoint_candidates.json
.env.cookie.local
```

`local_discovery/xipuai_endpoint_candidates.json` contains ranked candidate requests. `best_candidate` is usually the request you need.

`.env.cookie.local` contains a suggested configuration such as:

```text
XJGPT_ADAPTER_MODE=cookie
XIPUAI_CHAT_ENDPOINT=/example/chat/path
XIPUAI_API_METHOD=POST
XIPUAI_PAYLOAD_STYLE=openai
```

Review these values before using them. Do not commit local discovery files.

## Use the Suggested Endpoint

On PowerShell, set the values manually:

```powershell
$env:XJGPT_ADAPTER_MODE="cookie"
$env:XIPUAI_CHAT_ENDPOINT="/example/chat/path"
$env:XIPUAI_API_METHOD="POST"
$env:XIPUAI_PAYLOAD_STYLE="openai"
```

Then test:

```powershell
python scripts/test_cookie_http_adapter.py --question "请只回复两个字：成功" --model auto
```

If the test returns an answer, start the gateway:

```powershell
xjgpt-gateway --host 127.0.0.1 --port 8000
```

## How the Ranking Works

The helper gives higher scores to requests that:

- use POST;
- are XHR, fetch, event-stream, or similar dynamic requests;
- include request body fields such as `messages`, `question`, `prompt`, `content`, or `model`;
- return JSON or event-stream responses;
- contain the expected short answer in the response preview.

## Safety Notes

Do not send anyone your cookie values, authorization headers, token values, or `school_gpt_state.json` file. If you need help debugging, share only the endpoint path, method, payload field names, status code, and redacted screenshots.

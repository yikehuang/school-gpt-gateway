# GitHub Copilot Instructions for XJGPT

This repository contains XJGPT, a local school XipuAI gateway with a FastAPI backend and a ChatGPT-like frontend.

## Project structure

- `gateway.py`: FastAPI app and API endpoints.
- `school_gpt_adapter.py`: Playwright Web Adapter.
- `login_once.py`: local login-state capture.
- `static/`: frontend files.
- `xjgpt_gateway/`: package entry points.
- `docs/`: documentation and development records.

## Coding guidance

- Preserve `/v1/chat`, `/v1/chat/completions`, `/v1/models`, and `/` unless a task explicitly changes the API.
- Keep `web` / Playwright mode as the stable default path.
- Keep direct cookie/backend access experimental and opt-in.
- Keep frontend API settings compatible with `/v1/chat`.
- Update documentation when changing runtime behavior.

## Security restrictions

Do not suggest or add code that commits, logs, prints, or uploads:

- `school_gpt_state.json`
- cookies
- bearer tokens
- Authorization header values
- school passwords
- `.env` secrets
- local discovery outputs
- private request JSON files

Do not suggest CAPTCHA bypass, credential scraping, shared account automation, or CI calls to the real school XipuAI service.

## Validation

After code changes, run:

```bash
bash scripts/codex_check.sh
```

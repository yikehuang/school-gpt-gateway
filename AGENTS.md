# AGENTS.md

## Project overview

This repository contains **XJGPT**, a school XipuAI gateway project.

The stable application provides:

- A ChatGPT-like frontend under `static/`.
- A FastAPI gateway in `gateway.py`.
- A Playwright Web Adapter in `school_gpt_adapter.py`.
- Login-state capture through `login_once.py`.
- Package entry points under `xjgpt_gateway/`.
- Documentation under `docs/`.

Some branches may also contain an experimental Cookie HTTP Adapter. Treat that adapter as experimental unless the task explicitly targets it.

## Setup

Use Python 3.11 or later.

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

For local manual web-adapter testing, install Playwright browsers:

```bash
playwright install chromium
```

Do not run `xjgpt-login` in automated Codex or CI checks. That command requires a user-owned school login session.

## Safe validation

Run the Codex-safe check script after code changes:

```bash
bash scripts/codex_check.sh
```

This check must not call the real school XipuAI service and must not require `school_gpt_state.json`.

## Development rules

- Keep the Playwright Web Adapter as the stable default integration path.
- Preserve `/v1/chat`, `/v1/chat/completions`, `/v1/models`, and `/` unless the task explicitly changes API shape.
- When changing model selection, update both frontend model options and backend model mapping.
- Keep the frontend API settings panel compatible with `/v1/chat`.
- Prefer small, reviewable changes.
- Update documentation when changing setup, runtime behavior, API request format, model behavior, or adapter behavior.

## Security rules

Never commit or generate repository changes that include:

- `school_gpt_state.json`
- cookies
- raw `Cookie` headers
- `Authorization` token values
- school passwords
- `.env` files with secrets
- `local_discovery/` outputs
- private request dumps
- personal school account data

Never add code that:

- bypasses CAPTCHA or school authentication
- extracts credentials from users
- uploads cookies or login state
- prints cookie values, bearer tokens, or localStorage token values
- calls the school XipuAI backend from CI

## Important files

- `gateway.py`: FastAPI app and local API endpoints.
- `school_gpt_adapter.py`: Playwright Web Adapter for the school XipuAI page.
- `login_once.py`: local login-state capture helper.
- `static/index.html`: XJGPT frontend layout.
- `static/app.js`: frontend request logic.
- `static/styles.css`: frontend styling.
- `docs/DEVELOPMENT_LOG.md`: chronological development history.
- `docs/CODEX.md`: human-readable Codex usage guide.

## Expected response style for code work

When completing repository tasks, summarize:

1. Files changed.
2. Behavior changed.
3. Validation performed.
4. Any remaining manual steps.

If validation cannot be run, state the reason clearly.

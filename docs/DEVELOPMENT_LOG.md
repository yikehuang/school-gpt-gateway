# XJGPT Development Log

This document records the main project changes made during the XJGPT / school GPT gateway development process. It is intended to help reviewers understand how the repository evolved and what each stage added.

## 2026-06-22 — Initial school GPT gateway

The project started as a FastAPI-based gateway for a school web-based GPT service. The first version focused on wrapping the school GPT web page behind a local API.

Main changes:

- Added `gateway.py` as the FastAPI entry point.
- Added `school_gpt_adapter.py` as the Playwright Web Adapter.
- Added `login_once.py` to save a local browser login state as `school_gpt_state.json`.
- Added `/v1/chat` as the first gateway endpoint.
- Added request logging, latency measurement, and rough token estimation.
- Added `.gitignore` rules to prevent login state and private files from being committed.

Safety boundary:

- The gateway uses a local login state created by the user.
- The project does not store school account passwords in the repository.
- `school_gpt_state.json` must remain local and must not be uploaded to GitHub.

## 2026-06-22 — XipuAI school endpoint update

The school AI service URL was updated to XJTLU XipuAI:

```text
https://xipuai.xjtlu.edu.cn/v3/chat
```

Main changes:

- Updated `SCHOOL_GPT_URL` in the login and adapter files.
- Adjusted the documentation to describe XipuAI as the school GPT upstream service.
- Kept the Playwright Web Adapter as the default stable integration method.

## 2026-06-22 — XJGPT frontend

A ChatGPT-like frontend named **XJGPT** was added to make the project usable as a web application rather than only an API demo.

Main changes:

- Added `static/index.html` for the frontend layout.
- Added `static/styles.css` for the ChatGPT-like interface style.
- Added `static/app.js` for chat interaction and API calls.
- Updated `gateway.py` to serve the frontend at `/` and static assets under `/static`.
- Added sidebar, conversation area, input box, new chat button, status display, and example prompts.

Purpose:

- Users can open `http://127.0.0.1:8000` and use XJGPT directly.
- The frontend calls the local FastAPI gateway, and the gateway forwards the question to the school XipuAI page.

## 2026-06-22 — Model selection support

The project was extended to support model selection from the XJGPT frontend and to pass the selected model through the gateway.

Main changes:

- Added a model selector to the frontend.
- Added model IDs such as `auto`, `school-web-gpt`, `gpt-5.4`, `deepseek-r1`, `deepseek-v3`, and `qwen-max`.
- Added `/v1/models` to expose supported model metadata.
- Updated `/v1/chat` to accept a `model` value.
- Updated logs and API responses to record requested and runtime model information.
- Added model mapping logic so the Web Adapter can try to select the matching model in the XipuAI web interface.

Important note:

- The gateway can pass model choices to the adapter.
- Whether the school web page actually changes model depends on the real XipuAI DOM and model menu selectors.

## 2026-06-22 — OpenAI-style request compatibility

The gateway was updated to support a more standard `model + messages` JSON format.

Main changes:

- Added support for request bodies using `messages` arrays.
- Added compatibility with a request structure similar to OpenAI chat completions.
- Added `/v1/chat/completions` as an OpenAI-style endpoint.
- Added `examples/chat_request.example.json` as a safe example request.
- Kept older `question` style requests working.

Example request shape:

```json
{
  "model": "school-web-gpt",
  "messages": [
    {
      "role": "user",
      "content": "请只回复两个字：普通"
    }
  ]
}
```

## 2026-06-22 — Frontend API settings panel

The frontend was improved with software-level API configuration so the user can configure API calls inside XJGPT instead of editing code for basic settings.

Main changes:

- Added an API settings panel in the frontend.
- Added configurable API Base URL.
- Added configurable chat endpoint.
- Added configurable Bearer key field.
- Added request format selection: `messages` or `question`.
- Added request preview and API test support.

Purpose:

- XJGPT can be used as a configurable local client.
- The same frontend can test `/v1/chat` and compatible endpoints.

Security note:

- Hidden frontend keys are acceptable only for a local demo.
- A production deployment should not place real secrets in browser-side code.

## 2026-06-22 — Packaging and release support

The repository was prepared for packaging and release workflows.

Main changes:

- Added `pyproject.toml` for Python package metadata.
- Added `MANIFEST.in` for source distribution packaging.
- Added `xjgpt_gateway/` package entry points.
- Added `VERSION` and `CHANGELOG.md`.
- Added CLI commands such as `xjgpt-login` and `xjgpt-gateway`.
- Added release build scripts.
- Added GitHub workflow support for release artifacts.
- Added Docker / GitHub Container Registry configuration for package publication.

Purpose:

- The project can be installed with `pip install -e .`.
- The gateway can be started through a package command rather than only by running Python files directly.
- Releases and packages can be generated more consistently.

## 2026-06-22 — Documentation and wiki materials

Project documentation was expanded to make the repository easier to review and present.

Main changes:

- Added `docs/WIKI.md` as a wiki index.
- Added `docs/wiki/` pages for Home, Quick Start, Architecture, API Reference, Model Selection, Frontend, Packaging, Security Boundary, and Troubleshooting.
- Added a local wiki sync script for copying `docs/wiki/` into the GitHub Wiki repository.
- Added additional docs for frontend API settings, packaging, release, and security boundaries.

Note:

- GitHub Wiki uses an independent `.wiki.git` repository. If the GitHub connector cannot access it directly, the local sync script can be used instead.

## 2026-06-22 — Cookie HTTP Adapter experimental branch

A faster experimental path was created in a separate branch:

```text
feature/cookie-http-adapter
```

This branch keeps the stable Playwright Web Adapter but adds an experimental Cookie HTTP Adapter for direct backend calls when an authorized XipuAI backend endpoint is known.

Main changes:

- Added `adapter_router.py` to choose between `web` and `cookie` modes.
- Added `school_gpt_cookie_adapter.py` for local-cookie HTTP calls.
- Added `/v1/adapter` to inspect current adapter mode.
- Added `.env.cookie.example` for local configuration.
- Added `scripts/test_cookie_http_adapter.py` for local testing.
- Added `docs/COOKIE_HTTP_ADAPTER.md`.
- Added endpoint discovery tooling and documentation.

Safety boundary:

- Cookie values are read only from the local `school_gpt_state.json` generated by `xjgpt-login`.
- Cookie values must not be printed, uploaded, or committed.
- Cookie mode requires a locally configured and authorized backend endpoint through `XIPUAI_CHAT_ENDPOINT`.
- The default stable mode remains `web`.

## 2026-06-22 — Endpoint discovery automation

The cookie branch was extended with an endpoint discovery workflow to reduce manual browser inspection.

Main changes:

- Added `xjgpt-discover-endpoint` command.
- Added logic to open XipuAI locally, monitor network requests, and identify likely chat endpoints.
- Added output under `local_discovery/`.
- Added `.env.cookie.local` generation for local configuration.
- Updated `.gitignore` to keep local discovery outputs out of Git.

Purpose:

- Help the user discover possible XipuAI backend endpoints from their own authorized local session.
- Avoid committing sensitive tokens, cookies, or local traffic dumps.

## 2026-06-22 — Codex adaptation plan

A Codex adaptation plan was prepared so future AI-assisted coding work can be safer and more consistent.

Recommended changes:

- Add `AGENTS.md` with project-specific instructions for Codex.
- Add `scripts/codex_setup.sh` for dependency installation.
- Add `scripts/codex_check.sh` for safe validation.
- Add `docs/CODEX.md` to explain safe Codex usage.
- Add `.github/workflows/codex-check.yml` for CI checks.

Safety requirements for Codex:

- Codex must not commit cookies, tokens, `.env`, `school_gpt_state.json`, or local discovery outputs.
- Codex should not call the real school XipuAI backend in CI.
- Codex should preserve compatibility for `/v1/chat` and `/v1/chat/completions`.

## Current status summary

Stable branch:

```text
main
```

Contains:

- XJGPT frontend
- FastAPI gateway
- Playwright Web Adapter
- model selection support
- API settings panel
- OpenAI-style request compatibility
- packaging and release support
- documentation and wiki source files

Experimental branch:

```text
feature/cookie-http-adapter
```

Contains:

- all stable features
- Cookie HTTP Adapter framework
- endpoint discovery tooling
- local cookie-mode testing scripts

Recommended next steps:

1. Keep `main` as the stable demonstration branch.
2. Continue testing direct cookie/backend access in `feature/cookie-http-adapter`.
3. Add the Codex files in a separate `feature/codex-ready` branch before asking Codex to make larger code changes.
4. Avoid storing any real login state, cookie, token, or school account data in GitHub.

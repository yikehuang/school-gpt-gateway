# Changelog

## 0.1.0

Initial competition-ready release.

### Added

- XJGPT ChatGPT-like frontend.
- FastAPI gateway endpoints: `/v1/chat`, `/v1/chat/completions`, `/v1/models`.
- XipuAI web adapter based on Playwright.
- Model selection support for frontend and API payloads.
- Hidden demo API key in the frontend.
- OpenAI-style `messages` request support.
- Example JSON request under `examples/`.
- Python packaging metadata through `pyproject.toml`.
- Local release zip builder under `scripts/build_release.py`.
- GitHub Actions release workflow for tag-based releases.

### Safety

- `school_gpt_state.json`, `.env`, local JSON payloads, and logs are excluded from Git and release bundles.
- Request logs record lengths, model IDs, token estimates, and latency, not full user prompts or answers.

# Contributing

## Development Setup

```bash
python -m pip install -e ".[dev]"
```

If you need to run the live school adapter, install Playwright browsers:

```bash
playwright install chromium
```

## Local Checks

```bash
python -m compileall gateway.py school_gpt_adapter.py login_once.py xjgpt_gateway
pytest
```

## Safety Rules

- Do not commit login state, cookies, tokens, logs, or local config files.
- Keep live XipuAI calls out of unit tests.
- Prefer mocked adapter tests for gateway behavior.
- Update `docs/wiki/` when changing user-facing setup, API behavior, or security boundaries.

## Wiki Updates

The source pages live in `docs/wiki/`. After editing them, sync the official GitHub Wiki with:

```bash
python scripts/sync_wiki.py
```

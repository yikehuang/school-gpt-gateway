# Codex Quick Task Examples

Use these examples when asking Codex to work on this repository.

## Safe frontend task

```text
Improve the XJGPT frontend layout in static/index.html and static/styles.css. Keep /v1/chat request compatibility. Run bash scripts/codex_check.sh before finishing.
```

## Safe API task

```text
Refactor gateway.py to make request parsing clearer. Preserve /v1/chat and /v1/chat/completions response formats. Do not call XipuAI. Run bash scripts/codex_check.sh.
```

## Safe documentation task

```text
Update README.md and docs/CODEX.md to explain the current setup and validation flow. Do not change runtime behavior. Run bash scripts/codex_check.sh.
```

## Unsafe task examples

Do not ask Codex to do these:

```text
Log in to XipuAI and extract cookies.
```

```text
Commit my school_gpt_state.json so the app works in CI.
```

```text
Print all request headers including Cookie and Authorization.
```

Codex should refuse or redirect these tasks to safe local-only workflows.

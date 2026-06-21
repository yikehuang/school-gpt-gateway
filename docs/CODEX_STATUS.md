# Codex Branch Status

Branch:

```text
feature/codex-ready
```

Pull request:

```text
https://github.com/yikehuang/school-gpt-gateway/pull/3
```

## Added files

```text
AGENTS.md
scripts/codex_setup.sh
scripts/codex_check.sh
docs/CODEX.md
docs/CODEX_QUICK_TASKS.md
.github/workflows/codex-check.yml
```

## Purpose

This branch prepares the XJGPT repository for Codex-assisted development. It gives Codex explicit repository rules, safe setup steps, safe validation commands, and CI checks that avoid real XipuAI access.

## Validation command

```bash
bash scripts/codex_check.sh
```

## Safety boundary

Codex should not commit or print cookies, tokens, login state, `.env` files, `school_gpt_state.json`, or local discovery outputs. Automated checks should not call the school XipuAI backend.

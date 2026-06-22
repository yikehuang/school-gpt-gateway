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
docs/CODEX_STATUS.md
docs/AI_ASSISTANT_TOOLS.md
.github/workflows/codex-check.yml
.cursor/rules/xjgpt-project.mdc
.cursorrules
.github/copilot-instructions.md
.windsurfrules
.clinerules
```

## Purpose

This branch prepares the XJGPT repository for Codex-assisted development and other AI coding tools. It gives AI tools explicit repository rules, safe setup steps, safe validation commands, and CI checks that avoid real XipuAI access.

## Tool coverage

```text
Codex          -> AGENTS.md, docs/CODEX.md, scripts/codex_*.sh
Cursor         -> .cursor/rules/xjgpt-project.mdc, .cursorrules
GitHub Copilot -> .github/copilot-instructions.md
Windsurf       -> .windsurfrules
Cline          -> .clinerules
```

## Validation command

```bash
bash scripts/codex_check.sh
```

## Safety boundary

AI coding tools should not commit or print cookies, tokens, login state, `.env` files, `school_gpt_state.json`, or local discovery outputs. Automated checks should not call the school XipuAI backend.

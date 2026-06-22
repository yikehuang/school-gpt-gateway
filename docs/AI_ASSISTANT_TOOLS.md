# AI Assistant Tool Configuration

This branch adds repository-level configuration for multiple AI coding tools.

## Supported tools

```text
Codex        -> AGENTS.md, docs/CODEX.md, scripts/codex_*.sh
Cursor       -> .cursor/rules/xjgpt-project.mdc, .cursorrules
GitHub Copilot -> .github/copilot-instructions.md
Windsurf     -> .windsurfrules
Cline        -> .clinerules
```

## Shared rules

All tools should follow the same project constraints:

- XJGPT is a local school XipuAI gateway.
- `gateway.py` provides FastAPI endpoints.
- `school_gpt_adapter.py` is the stable Playwright Web Adapter.
- `static/` contains the frontend.
- `/v1/chat` and `/v1/chat/completions` should remain compatible.
- The Playwright Web Adapter remains the default stable mode.
- Direct cookie/backend access is experimental and opt-in.

## Security boundary

AI coding tools must not commit, print, upload, or generate examples containing:

- `school_gpt_state.json`
- cookies
- raw `Cookie` headers
- bearer tokens or Authorization values
- school passwords
- `.env` secrets
- `local_discovery/` outputs
- private request dumps
- personal school account data

AI coding tools must not add code for:

- CAPTCHA bypass;
- credential scraping;
- hidden shared-account automation;
- uploading login state;
- calling XipuAI from CI.

## Validation command

Use this command after AI-assisted changes:

```bash
bash scripts/codex_check.sh
```

The validation script is intentionally tool-neutral. It can be used after Codex, Cursor, GitHub Copilot, Windsurf, Cline, or manual edits.

## Recommended workflow

1. Open the repository in the coding tool.
2. Confirm the tool has loaded the relevant rule file.
3. Ask for one small change at a time.
4. Run `bash scripts/codex_check.sh`.
5. Review diffs before committing.

## Example safe prompt

```text
Refactor gateway.py to make request parsing clearer. Preserve /v1/chat and /v1/chat/completions behavior. Do not call XipuAI. Run bash scripts/codex_check.sh before finishing.
```

## Example unsafe prompt

```text
Read my school_gpt_state.json and commit it so the project works for everyone.
```

The tool should reject or redirect unsafe prompts to local-only workflows.

# Codex Integration Guide

This repository is prepared for Codex-assisted development. The purpose of this document is to explain what Codex may safely change, how Codex should validate changes, and what manual steps remain outside automated checks.

## Branch

Codex adaptation work is kept in:

```text
feature/codex-ready
```

This branch should remain separate from the experimental Cookie HTTP Adapter branch unless the task explicitly asks to combine them.

## Recommended Codex tasks

Good Codex tasks include:

- Refactor `gateway.py` without changing public endpoints.
- Improve frontend UI files under `static/`.
- Improve request validation for `/v1/chat` and `/v1/chat/completions`.
- Add safe unit tests that do not call XipuAI.
- Improve documentation and README instructions.
- Add model-mapping validation.
- Improve local packaging and release scripts.

Avoid Codex tasks that require:

- Logging into XipuAI.
- Reading or uploading `school_gpt_state.json`.
- Discovering private endpoints in CI.
- Calling the real school backend from GitHub Actions.
- Printing cookies, bearer tokens, localStorage tokens, or school account data.

## Setup for Codex

Use the setup script:

```bash
bash scripts/codex_setup.sh
```

The setup script installs dependencies and runs the safe validation script. It does not log into XipuAI and does not require a local browser login state.

## Safe validation

Run:

```bash
bash scripts/codex_check.sh
```

The validation script checks:

- Python syntax compilation.
- FastAPI app import.
- Presence of expected routes.
- Presence of frontend files.
- Absence of sensitive local files.

It deliberately avoids:

- running `xjgpt-login`;
- opening XipuAI;
- calling the school backend;
- loading real cookies or tokens.

## Repository instructions

Codex should read `AGENTS.md` before modifying files. That file contains project rules, security rules, and expected validation steps.

## Runtime testing outside Codex

Manual runtime testing still requires a user-owned local session:

```bash
xjgpt-login
xjgpt-gateway --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

The local `school_gpt_state.json` file created by `xjgpt-login` must not be committed.

## Security boundary

This project is for authorized school GPT access. Codex should preserve this boundary in all generated changes.

Never add code that bypasses school authentication, harvests credentials, uploads cookies, or hides unauthorized request replay behavior.

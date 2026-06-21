# Packaging Guide

This guide explains how to package XJGPT for local submission, demo handoff, or GitHub Release assets.

## 1. Install Build Tools

```bash
python -m pip install --upgrade pip build
```

## 2. Build Python Package

```bash
python -m build
```

The command creates:

```text
dist/*.tar.gz
dist/*.whl
```

## 3. Build Release Zip

```bash
python scripts/build_release.py
```

The script creates:

```text
release/xjgpt-school-gateway-0.1.0.zip
```

The zip contains the project source, frontend files, examples, and documentation. It does not include local login state or private test payloads.

## 4. Files Excluded From Package/Release

The release process excludes:

```text
school_gpt_state.json
.env
*.local.json
request.json
private_request.json
*.log
__pycache__/
.venv/
venv/
build/
dist/
release/
```

`school_gpt_state.json` is created after `python login_once.py`. It contains local browser login state and must remain on the user's own computer.

## 5. Install Locally As A Package

For development:

```bash
pip install -e .
```

Then run:

```bash
xjgpt-login
xjgpt-gateway --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

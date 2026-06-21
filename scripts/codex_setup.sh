#!/usr/bin/env bash
set -euo pipefail

echo "[setup] Python version"
python --version

echo "[setup] Upgrade pip"
python -m pip install --upgrade pip

echo "[setup] Install project dependencies"
pip install -r requirements.txt

if [ -f pyproject.toml ]; then
  echo "[setup] Install package in editable mode"
  pip install -e .
fi

if command -v playwright >/dev/null 2>&1; then
  echo "[setup] Playwright is installed"
  echo "[setup] Browser installation is optional for Codex-safe checks"
else
  echo "[setup] Playwright command not found; continuing because safe checks do not need a browser"
fi

echo "[setup] Run Codex-safe validation"
bash scripts/codex_check.sh

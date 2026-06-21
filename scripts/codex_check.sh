#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Compile Python source files"
python - <<'PY'
from pathlib import Path
import py_compile
import sys

roots = [Path('.'), Path('xjgpt_gateway'), Path('scripts')]
skip_dirs = {'.git', '.venv', 'venv', 'env', '__pycache__', 'dist', 'build', 'release', 'local_discovery'}
errors = []
seen = set()

for root in roots:
    if not root.exists():
        continue
    paths = [root] if root.is_file() else root.rglob('*.py')
    for path in paths:
        if path.is_dir():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path in seen:
            continue
        seen.add(path)
        try:
            py_compile.compile(str(path), doraise=True)
            print(f"compiled {path}")
        except Exception as exc:
            errors.append((path, exc))

if errors:
    for path, exc in errors:
        print(f"ERROR compiling {path}: {exc}", file=sys.stderr)
    sys.exit(1)
PY

echo "[2/5] Import FastAPI app without logging into XipuAI"
python - <<'PY'
import gateway

assert hasattr(gateway, 'app'), 'gateway.app is missing'
route_paths = {getattr(route, 'path', '') for route in gateway.app.routes}
required_any = {'/', '/v1/chat'}
missing = [path for path in required_any if path not in route_paths]
if missing:
    raise SystemExit(f"Missing expected routes: {missing}")
print('FastAPI app loaded')
print('Routes:', ', '.join(sorted(path for path in route_paths if path)))
PY

echo "[3/5] Check frontend files"
test -f static/index.html
test -f static/app.js
test -f static/styles.css

echo "[4/5] Check documentation files"
test -f README.md
test -f docs/DEVELOPMENT_LOG.md
if [ -f AGENTS.md ]; then
  grep -q "school_gpt_state.json" AGENTS.md
fi

echo "[5/5] Check that sensitive local files are absent"
test ! -f school_gpt_state.json
test ! -f .env
test ! -d local_discovery

echo "Codex check passed."

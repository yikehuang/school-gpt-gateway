"""Build a local release bundle for XJGPT.

This script creates:
- dist/*.tar.gz and dist/*.whl through `python -m build`
- release/xjgpt-school-gateway-<version>.zip for direct upload/demo handoff

It intentionally excludes local login/session/private files.
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"

EXCLUDE_PATTERNS = [
    ".git/*",
    ".github/*",
    "__pycache__/*",
    "*.pyc",
    ".venv/*",
    "venv/*",
    "env/*",
    "build/*",
    "dist/*",
    "release/*",
    ".env",
    "school_gpt_state.json",
    "*.local.json",
    "request.json",
    "private_request.json",
    "*.log",
]

INCLUDE_PATHS = [
    "gateway.py",
    "school_gpt_adapter.py",
    "login_once.py",
    "requirements.txt",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "MANIFEST.in",
    "VERSION",
    "examples",
    "static",
    "docs",
    "tests",
    "xjgpt_gateway",
]


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "0.1.0"


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    for pattern in EXCLUDE_PATTERNS:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel + "/", pattern):
            return True
    return False


def iter_release_files():
    for item in INCLUDE_PATHS:
        path = ROOT / item
        if not path.exists():
            continue
        if path.is_file() and not should_exclude(path):
            yield path
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and not should_exclude(child):
                    yield child


def build_python_package() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "build"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "build"], cwd=ROOT, check=True)


def build_zip(version: str) -> Path:
    release_dir = ROOT / "release"
    release_dir.mkdir(exist_ok=True)
    zip_path = release_dir / f"xjgpt-school-gateway-{version}.zip"

    if zip_path.exists():
        zip_path.unlink()

    top_dir = f"xjgpt-school-gateway-{version}"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in iter_release_files():
            arcname = Path(top_dir) / file_path.relative_to(ROOT)
            zf.write(file_path, arcname.as_posix())

    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build XJGPT release artifacts.")
    parser.add_argument("--skip-python-package", action="store_true", help="Only build the release zip.")
    args = parser.parse_args()

    version = read_version()

    if not args.skip_python_package:
        build_python_package()

    zip_path = build_zip(version)
    print(f"Release zip created: {zip_path}")


if __name__ == "__main__":
    main()

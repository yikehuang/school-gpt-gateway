"""Sync docs/wiki Markdown files to the GitHub Wiki repository.

Usage:
    python scripts/sync_wiki.py

Requirements:
    - git installed
    - permission to push to https://github.com/yikehuang/school-gpt-gateway.wiki.git
    - GitHub Wiki has been initialized at least once in the web UI
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "docs" / "wiki"
WIKI_REPO_URL = "https://github.com/yikehuang/school-gpt-gateway.wiki.git"


def run(command: list[str], cwd: Path | None = None) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def get_repo_config(key: str) -> str | None:
    result = subprocess.run(
        ["git", "config", "--get", key],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value or None


def configure_commit_identity(wiki_dir: Path) -> None:
    for key in ("user.name", "user.email"):
        value = get_repo_config(key)
        if value:
            run(["git", "config", key, value], cwd=wiki_dir)


def main() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Wiki source directory not found: {SOURCE_DIR}")

    with tempfile.TemporaryDirectory(prefix="xjgpt-wiki-") as temp_dir:
        wiki_dir = Path(temp_dir) / "wiki"

        run(["git", "clone", WIKI_REPO_URL, str(wiki_dir)])
        configure_commit_identity(wiki_dir)

        # Remove existing Markdown pages in the Wiki clone.
        for path in wiki_dir.glob("*.md"):
            path.unlink()

        # Copy current Wiki pages from docs/wiki.
        for source in SOURCE_DIR.glob("*.md"):
            target = wiki_dir / source.name
            shutil.copy2(source, target)
            print(f"copied {source.relative_to(ROOT)} -> {target.name}")

        run(["git", "add", "."], cwd=wiki_dir)

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wiki_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        if not status.stdout.strip():
            print("No Wiki changes to commit.")
            return

        run(["git", "commit", "-m", "Sync project wiki"], cwd=wiki_dir)
        run(["git", "push", "origin", "master"], cwd=wiki_dir)

        print("GitHub Wiki sync completed.")


if __name__ == "__main__":
    main()

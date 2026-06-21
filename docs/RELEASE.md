# Release Guide

This project supports two release paths: local release zip and GitHub tag release.

## 1. Local Release Zip

Run:

```bash
python scripts/build_release.py
```

The output will be placed under:

```text
release/
```

Use this zip for course submission or offline demo transfer.

## 2. GitHub Release

GitHub Actions will create a release when a tag beginning with `v` is pushed.

Example:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The release workflow will:

1. install Python;
2. install project build dependencies;
3. build source distribution and wheel;
4. build the release zip;
5. upload artifacts to the GitHub Release page.

## 3. Version Update Checklist

Before creating a new tag, update these files consistently:

```text
VERSION
pyproject.toml
xjgpt_gateway/__init__.py
CHANGELOG.md
```

## 4. Security Checklist

Before release, confirm these files are not committed:

```text
school_gpt_state.json
.env
*.local.json
request.json
private_request.json
*.log
```

The repository `.gitignore`, `MANIFEST.in`, and release script already exclude these files, but the maintainer should still check manually before publishing.

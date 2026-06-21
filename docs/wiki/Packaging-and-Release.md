# Packaging and Release

本页说明项目的 Python package、Docker package 和 GitHub Release 配置。

## 1. Python Package

项目使用 `pyproject.toml` 配置 Python package。

安装方式：

```bash
pip install -e .
```

安装后提供两个命令行入口：

```bash
xjgpt-login
xjgpt-gateway --host 127.0.0.1 --port 8000
```

## 2. 本地构建 Release Zip

运行：

```bash
python scripts/build_release.py
```

生成文件：

```text
release/xjgpt-school-gateway-0.1.0.zip
```

打包脚本会排除敏感文件，例如：

```text
school_gpt_state.json
.env
*.local.json
request.json
private_request.json
*.log
```

## 3. GitHub Release

仓库包含 `.github/workflows/release.yml`。该 workflow 可以在以下情况下运行：

- push 到 `main` 分支；
- push `v*` tag；
- 手动点击 `Actions -> Release -> Run workflow`。

推荐正式发版方式：

```bash
git tag v0.1.0
git push origin v0.1.0
```

workflow 会构建：

```text
dist/*.tar.gz
dist/*.whl
release/*.zip
```

并上传到 GitHub Release。

## 4. Docker Package

项目包含 `Dockerfile` 和 `.dockerignore`。GitHub Actions 会构建 Docker image 并推送到 GitHub Container Registry。

目标 package：

```text
ghcr.io/yikehuang/school-gpt-gateway
```

如果右侧 Packages 没有显示，可以检查：

1. GitHub Actions 是否成功运行；
2. workflow 是否有 `packages: write` 权限；
3. image 名称是否和当前仓库绑定；
4. Dockerfile 是否包含 `org.opencontainers.image.source` 标签；
5. package 可见性是否设为公开。

## 5. 手动运行 Release Workflow

在 GitHub 页面：

```text
Actions
→ Release
→ Run workflow
→ Run workflow
```

运行完成后，仓库右侧应显示：

```text
Releases: v0.1.0
Packages: school-gpt-gateway
```

如果 workflow 失败，需要打开失败日志，重点检查 Docker login、package permission 和 build step。

## 6. 不应发布的内容

以下内容不应进入 Release 或 Package：

```text
school_gpt_state.json
.env
任何真实账号密码
包含隐私对话的 JSON
个人 Cookie
浏览器缓存
```

这些文件已经通过 `.gitignore`、`.dockerignore` 和 release 打包脚本排除。

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment not found: $Python"
}

Set-Location -LiteralPath $ProjectRoot
& $Python (Join-Path $PSScriptRoot "start_pinggy_tunnel.py")

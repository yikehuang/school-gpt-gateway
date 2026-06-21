param(
    [string]$Url = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ToolsDir = Join-Path $ProjectRoot "tools"
$Cloudflared = Join-Path $ToolsDir "cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

if (-not (Test-Path -LiteralPath $ToolsDir)) {
    New-Item -ItemType Directory -Path $ToolsDir | Out-Null
}

if (-not (Test-Path -LiteralPath $Cloudflared)) {
    Write-Host "Downloading cloudflared..."
    Invoke-WebRequest -UseBasicParsing -Uri $DownloadUrl -OutFile $Cloudflared
}

Write-Host "Starting Cloudflare Quick Tunnel for $Url"
Write-Host "Keep this window open while you need the public URL."
& $Cloudflared tunnel --url $Url

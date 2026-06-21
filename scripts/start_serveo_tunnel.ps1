$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$KnownHosts = Join-Path $ProjectRoot "serveo-known-hosts"

Set-Location -LiteralPath $ProjectRoot
Write-Host "Starting Serveo tunnel for http://127.0.0.1:8000"
Write-Host "Use the printed serveousercontent.com URL as the public Base URL."
Write-Host "For external API clients, prefer stream=true because Serveo may time out non-streaming requests."

ssh `
    -o StrictHostKeyChecking=accept-new `
    -o "UserKnownHostsFile=$KnownHosts" `
    -o ServerAliveInterval=30 `
    -o ExitOnForwardFailure=yes `
    -R 80:127.0.0.1:8000 `
    serveo.net

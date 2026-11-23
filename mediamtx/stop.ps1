# Stops the MediaMTX started by start.ps1 (only that process).
$pidFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "mediamtx.pid"
if (Test-Path $pidFile) {
    Stop-Process -Id (Get-Content $pidFile) -ErrorAction SilentlyContinue
    Remove-Item $pidFile
    Write-Host "MediaMTX stopped"
} else { Write-Host "not running (no pid file)" }

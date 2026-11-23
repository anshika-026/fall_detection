# Starts the Fall Detection backend in its OWN window, independent of VS Code and of any terminal, on http://127.0.0.1:8830
# (the web UI is served from the same address). Only touches this project. Safe to run again: it refuses if port 8830 is already in use.
#   Start :  powershell -ExecutionPolicy Bypass -File "C:\Users\lenovo\Desktop\FALL DETECTION\run_fall_detection.ps1"
#   Stop  :  powershell -ExecutionPolicy Bypass -File "C:\Users\lenovo\Desktop\FALL DETECTION\run_fall_detection.ps1" -Stop
param([switch]$Stop)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$logs = Join-Path $root "validation\results"
$py = (Get-Command python -ErrorAction Stop).Source

function Get-FdBackend { Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'falldet\.serve' } }

if ($Stop) {
    $p = @(Get-FdBackend)
    if (-not $p) { "Fall Detection backend is not running."; exit 0 }
    $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; "stopped Fall Detection backend (pid $($_.ProcessId))" }
    exit 0
}
if (Get-NetTCPConnection -State Listen -LocalPort 8830 -ErrorAction SilentlyContinue) {
    "Port 8830 is already in use (Fall Detection may already be running): http://127.0.0.1:8830"; exit 1
}
New-Item -ItemType Directory -Force $logs | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
Start-Process -FilePath $py -ArgumentList "-m", "falldet.serve" -WorkingDirectory $backend -WindowStyle Minimized `
    -RedirectStandardOutput (Join-Path $logs "backend_$stamp.log") -RedirectStandardError (Join-Path $logs "backend_$stamp.err.log")
"Started. Open http://127.0.0.1:8830 in a few seconds (logs: validation\results\backend_$stamp.log)"

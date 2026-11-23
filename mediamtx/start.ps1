# Starts MediaMTX in the background (localhost RTSP on 8554). Stop with stop.ps1.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $here "bin\mediamtx.exe"
$pidFile = Join-Path $here "mediamtx.pid"
if (-not (Test-Path $exe)) { Write-Error "bin\mediamtx.exe missing: extract the MediaMTX release zip into mediamtx\bin (see README.md)"; exit 1 }
if ((Test-Path $pidFile) -and (Get-Process -Id (Get-Content $pidFile) -ErrorAction SilentlyContinue)) { Write-Host "already running"; exit 0 }
$p = Start-Process -FilePath $exe -ArgumentList (Join-Path $here "mediamtx.yml") -WorkingDirectory $here `
     -RedirectStandardOutput (Join-Path $here "mediamtx.log") -RedirectStandardError (Join-Path $here "mediamtx.err.log") -WindowStyle Hidden -PassThru
$p.Id | Set-Content $pidFile
Write-Host "MediaMTX started, pid $($p.Id), rtsp://127.0.0.1:8554"

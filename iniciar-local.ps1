$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$pgCtl = Join-Path $PSScriptRoot '.runtime\pgsql\bin\pg_ctl.exe'
& $pgCtl -D .runtime\pgdata status *> $null
if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D .runtime\pgdata -l .runtime\postgres.log -o '-p 55432 -h 127.0.0.1' -w start
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar PostgreSQL.' }
}

if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) {
    Write-Host 'Ya hay un servidor escuchando en http://127.0.0.1:8000.'
    exit 0
}

& '.\.venv\Scripts\python.exe' manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron aplicar las migraciones.' }

Write-Host 'Aplicación: http://127.0.0.1:8000 (Ctrl+C para detener el servidor)'
& '.\.venv\Scripts\python.exe' manage.py runserver 127.0.0.1:8000

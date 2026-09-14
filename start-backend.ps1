$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host 'Comprobando entorno virtual y backend\.env antes de arrancar Django.'
if (-not (Test-Path 'backend\.venv\Scripts\python.exe')) {
    throw 'Falta backend\.venv. Ejecuta .\setup-local.ps1 primero.'
}
if (-not (Test-Path 'backend\.env')) {
    throw 'Falta backend\.env. Copia backend\.env.example, completa tus claves y no lo subas a Git.'
}

Write-Host 'Iniciando Django en http://127.0.0.1:8000/ (Swagger en /api/docs/). Detener con Ctrl+C.'
& 'backend\.venv\Scripts\python.exe' 'backend\manage.py' runserver 127.0.0.1:8000

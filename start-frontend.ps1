$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ProjectRoot 'frontend')

Write-Host 'Comprobando dependencias de Node antes de arrancar Vite.'
if (-not (Test-Path 'node_modules')) {
    throw 'Falta frontend\node_modules. Ejecuta .\setup-local.ps1 primero.'
}
if (-not (Test-Path '.env') -and (Test-Path '.env.example')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Se creo frontend\.env desde el ejemplo. No agregues secretos en ese archivo.'
}

Write-Host 'Iniciando Vite. La URL suele ser http://localhost:5173. El frontend llama solo a VITE_API_URL. Detener con Ctrl+C.'
npm run dev

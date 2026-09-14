$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host 'Paso 1/7: Comprobar Python 3.11+ y Node.js 20+ en PATH.'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python no esta instalado o no esta en PATH. Instala Python 3.11 o superior y vuelve a ejecutar este script.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js no esta instalado o no esta en PATH. Instala Node.js 20 o superior y vuelve a ejecutar este script.'
}

Write-Host 'Paso 2/7: Crear el entorno virtual en backend\.venv si no existe.'
if (-not (Test-Path 'backend\.venv\Scripts\python.exe')) {
    python -m venv backend\.venv
}

$Python = (Resolve-Path 'backend\.venv\Scripts\python.exe').Path

Write-Host 'Paso 3/7: Instalar dependencias de Python (backend\requirements.txt).'
& $Python -m pip install --upgrade pip
& $Python -m pip install -r backend\requirements.txt

Write-Host 'Paso 4/7: Crear archivos .env locales a partir de los ejemplos, sin sobrescribir los existentes.'
if (-not (Test-Path 'backend\.env')) {
    if (-not (Test-Path 'backend\.env.example')) {
        throw 'Falta backend\.env.example. No se puede crear backend\.env.'
    }
    Copy-Item 'backend\.env.example' 'backend\.env'
    Write-Host 'Se creo backend\.env. Debes reemplazar los valores de ejemplo por tus claves y tu password de PostgreSQL.'
}
if (-not (Test-Path 'frontend\.env')) {
    if (Test-Path 'frontend\.env.example') {
        Copy-Item 'frontend\.env.example' 'frontend\.env'
        Write-Host 'Se creo frontend\.env con VITE_API_URL local. No agregues tokens en ese archivo.'
    }
}

Write-Host 'Paso 5/7: Instalar dependencias de Node en frontend\.'
Push-Location frontend
npm install
Pop-Location

Write-Host 'Paso 6/7: Aplicar migraciones de Django. PostgreSQL debe estar en marcha y backend\.env debe tener DB_* correctos.'
try {
    & $Python backend\manage.py migrate
}
catch {
    Write-Host 'La migracion fallo. Completa DB_NAME, DB_USER, DB_PASSWORD, DB_HOST y DB_PORT en backend\.env, crea la base chatbot_db y vuelve a ejecutar este script.'
    throw
}

Write-Host 'Paso 7/7: Preparacion terminada.'
Write-Host 'Siguiente: edita backend\.env con tus claves (Jira, PostgreSQL, Django). Luego arranca .\start-backend.ps1 y .\start-frontend.ps1.'
Write-Host 'OPENAI_API_KEY y GEMINI_API_KEY solo son necesarias si usas Codex o agy. El chat Python funciona sin ellas.'
Write-Host 'Si usas datos Excel locales, ejecuta: backend\.venv\Scripts\python.exe backend\manage.py import_jira_excel'

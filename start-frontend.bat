@echo off
cd /d "%~dp0frontend"
echo Arrancando el frontend Vite. Si faltan dependencias, ejecuta setup-local.bat en la raiz del repo.
if not exist "node_modules" (
  echo Faltan dependencias. Ejecuta setup-local.bat primero.
  pause
  exit /b 1
)
if not exist ".env" (
  if exist ".env.example" copy ".env.example" ".env" >nul
)
npm run dev

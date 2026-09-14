@echo off
setlocal
cd /d "%~dp0"
echo Ejecutando setup-local.ps1 (instalacion de entorno, dependencias y migraciones).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-local.ps1"
if errorlevel 1 (
  echo La preparacion fallo. Revisa el mensaje anterior, PostgreSQL y backend\.env.
  pause
  exit /b 1
)
echo Preparacion correcta. Edita backend\.env con tus propias claves antes de arrancar los servidores.
pause

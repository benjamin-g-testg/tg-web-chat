@echo off
cd /d "%~dp0"
echo Arrancando el backend Django. Si falla, ejecuta setup-local.bat y completa backend\.env.
if not exist "backend\.venv\Scripts\python.exe" (
  echo Falta el entorno virtual. Ejecuta setup-local.bat primero.
  pause
  exit /b 1
)
if not exist "backend\.env" (
  echo Falta backend\.env. Copia backend\.env.example y pon tus propias claves.
  pause
  exit /b 1
)
"backend\.venv\Scripts\python.exe" backend\manage.py runserver 127.0.0.1:8000

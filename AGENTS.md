# Instrucciones del proyecto ChatBot QA

Antes de cambiar código, leer `PROJECT_CONTEXT.md` y preservar la arquitectura de capas del backend.

- Backend: Django + DRF + PostgreSQL en `backend/`.
- Frontend: React + Vite en `frontend/`.
- Los secretos viven solamente en archivos `.env` locales; nunca se deben confirmar en Git.
- Las migraciones de Django son la fuente de verdad del esquema. No crear tablas manualmente en PostgreSQL.
- Los datos Jira se importan desde `TestGroup/DATOS_IA_HISTORICO.xlsx` usando `python manage.py import_jira_excel`.
- Antes de declarar una tarea terminada, verificar migraciones, importación o compilación según corresponda.

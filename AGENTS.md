# Instrucciones del proyecto ChatBot QA

Antes de cambiar codigo, leer `PROJECT_CONTEXT.md` y preservar la arquitectura de capas del backend.

## Capas

- Backend: Django + DRF + PostgreSQL en `backend/`.
- Frontend: React + Vite + TypeScript en `frontend/`.
- Integracion Jira y calculo de metricas: `src.integrations.jira_client`. No reintroducir `metrics_service.py`.
- Intenciones de chat: `src.agents.agent_service.JiraAgent`.
- Pipeline QA determinista: `src.core.services.run_qa_pipeline`.
- Agente local opcional (Codex / Antigravity): `src.agents.local_agent_service`.
- Vistas HTTP: `src.api.views`. El frontend solo llama a `/api/*`.

## Seguridad

- Los secretos viven exclusivamente en archivos `.env` locales. Nunca confirmarlos en Git.
- El frontend no debe contener tokens de Jira, OpenAI, Gemini ni contrasenas de base de datos.
- Toda consulta de chat se valida por longitud y se sanitiza contra XSS en `ChatView`.
- No hardcodear passwords en `settings.py` ni en `README.md`.

## Datos

- Las migraciones de Django son la fuente de verdad del esquema. No crear tablas manualmente en PostgreSQL.
- Fuente Jira Cloud: `JIRA_DATA_SOURCE=jira` con `JIRA_SERVER`, `JIRA_USER` y `JIRA_API_TOKEN` propios.
- Fuente local: `JIRA_DATA_SOURCE=local` e importar Excel con `python manage.py import_jira_excel` (opcional `--file`).
- El Excel historico por defecto se busca en `TestGroup/DATOS_IA_HISTORICO.xlsx` (un nivel por encima de este repositorio).

## Frontend

- Estilo profesional y sobrio.
- Iconos SVG vectoriales. No usar emojis en la interfaz ni en la documentacion del repositorio.

## Antes de declarar una tarea terminada

- Backend: `python manage.py test src.api.tests --keepdb` (desde `backend/`, con `.venv` activo).
- Frontend: `npm run build` (desde `frontend/`).

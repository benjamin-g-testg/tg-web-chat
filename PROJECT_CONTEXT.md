# Contexto persistente: ChatBot QA

## Objetivo

Aplicacion web de analisis interactivo de calidad sobre datos Jira, con chat, metricas KPI y reportes descargables. El frontend (React + Vite) consume una API REST (Django + DRF). La persistencia es PostgreSQL local. El procesamiento de metricas y filtros deterministas ocurre solo en Python. El navegador no llama a Jira ni a proveedores de IA.

## Estado tecnico actual

- **Base de datos**: PostgreSQL, configurada con variables de `backend/.env` (nombre sugerido `chatbot_db`, puerto 5432).
- **Esquema**: modelos `Session`, `ChatMessage`, `AnalysisExecution`, `AnalysisJob` y `JiraIssue`.
- **Integracion Jira**: `src/integrations/jira_client.py`. Dual:
  - `JIRA_DATA_SOURCE=jira`: REST de Jira Cloud (proyecto TATC).
  - `JIRA_DATA_SOURCE=local`: tabla `JiraIssue` (pruebas o Excel).
- **Clasificacion de estados**: categorias globales de Jira `done`, `indeterminate` y `new`, mas deteccion de bloqueos.
- **Chat**: `POST /api/chat/` valida y sanitiza el mensaje, detecta intencion con `JiraAgent`, ejecuta `run_qa_pipeline` (metricas + respuesta en lenguaje natural), opcionalmente llama al agente local, genera Word/PDF y persiste sesion, mensajes, job y ejecucion.
- **Otros endpoints**:
  - `GET /api/sessions/`
  - `GET|PATCH|DELETE /api/sessions/<uuid:session_id>/`
  - `GET /api/metrics/` (`exclude_subtasks`, `debug`)
  - `GET /api/jobs/<uuid:job_id>/`
  - `GET /api/jobs/<uuid:job_id>/artifacts/<format>/<filename>`
  - `GET /api/artifacts/`
  - `GET /api/docs/` (Swagger)
- **Frontend**: React + TypeScript + Vite. Restaura sesiones, muestra KPI, pestañas de reporte (Fase 1, Fase 2, Fase 3, Conclusion, Resumen ejecutivo), descarga Word/PDF y exporta Excel. Sin emojis. Paleta corporativa.

## Comprension de lenguaje natural

`JiraAgent` interpreta espanol coloquial (acentos, sinonimos, claves `TATC-n`, "ticket 8", "mis asignados", estados, bloqueos, reportes). El pipeline responde con los issues y metricas reales. No es un asistente de proposito general: el alcance es QA/Jira del proyecto TATC.

## Comandos operativos

Ver `README.md` para el procedimiento completo de clonado. Resumen con `.venv` activo en `backend/`:

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py import_jira_excel
python manage.py test src.api.tests --keepdb
python manage.py runserver
```

Desde `frontend/`:

```powershell
npm install
npm run build
npm run dev
```

## Scripts

- `setup-local.ps1` / `setup-local.bat`: entorno virtual, dependencias, copia de `.env.example` y migraciones.
- `start-backend.ps1` / `start-backend.bat`: Django en `127.0.0.1:8000`.
- `start-frontend.ps1` / `start-frontend.bat`: Vite en el puerto 5173.
- `scripts/run_agent_local.ps1`: harness opcional de agente CLI contra un issue Jira. Requiere claves propias.

## Decisiones y precauciones

- No confirmar `backend/.env`, `frontend/.env`, `.venv`, `node_modules` ni artefactos en `04_Resultado_del_Analisis/`.
- Cada clon debe usar sus propias claves (Jira, PostgreSQL, OpenAI/Gemini si aplica) y su propia `DJANGO_SECRET_KEY`.
- Si una credencial llego a Git o a un README, rotarla en el proveedor y reemplazarla en el `.env` local.
- Cero exposicion de secretos en el cliente frontend.
- Toda entrada de usuario en `ChatView` pasa por validacion de longitud y sanitizacion XSS.

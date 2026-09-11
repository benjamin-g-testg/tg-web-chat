# Contexto persistente: ChatBot QA

## Objetivo

Aplicación web para análisis de calidad de datos Jira mediante una interfaz de chat. El frontend consume una API Django y los resultados, sesiones y datos Jira se guardan en PostgreSQL local.

## Estado técnico actual

- PostgreSQL configurado en `backend/.env`: base `chatbot_db`, host local, puerto 5432.
- El esquema Django contiene `Session`, `ChatMessage`, `AnalysisExecution` y `JiraIssue`.
- `JiraIssue` se crea en la migración `database/0002_jiraissue` para evitar cambiar la migración inicial ya aplicada.
- El archivo fuente está en `TestGroup/DATOS_IA_HISTORICO.xlsx`; tiene 99 filas en la hoja `JiraData_1_1_B`.
- La carga se ejecuta con `python manage.py import_jira_excel`; es idempotente, por lo que actualiza por `jira_id` sin duplicar registros.
- Swagger está disponible en `/api/docs/`; OpenAPI JSON en `/api/schema/`.

## Comandos operativos

Desde `backend/`, con `.venv` activo:

```powershell
pip install -r requirements.txt
python manage.py migrate database
python manage.py import_jira_excel
python manage.py runserver
```

Comprobaciones:

```powershell
python manage.py shell -c 'from src.database.models import JiraIssue; print(JiraIssue.objects.count())'
```

Resultado esperado: `99`.

## Decisiones y precauciones

- No confirmar `backend/.env`, `.venv`, `node_modules` ni archivos generados; `.gitignore` lo impide.
- El historial contiene keys Jira que probablemente ya existen en Jira Cloud. No reimportarlos como issues nuevos sin una estrategia de sincronización, pues se crearían duplicados.
- Para integrar con Jira Cloud de forma automática se requieren URL del sitio, proyecto destino y un token API guardado localmente como variable de entorno, nunca dentro del repositorio ni en el chat.

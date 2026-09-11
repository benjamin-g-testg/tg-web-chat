# ChatBot · QA Jira

Aplicación SPA de análisis QA con Django REST Framework, PostgreSQL y React/Vite.

## Base de datos (pgAdmin 4)

1. Abra pgAdmin 4, conéctese al servidor local PostgreSQL con el usuario `postgres` y contraseña `pokemega`.
2. En **Databases**, seleccione **Create > Database**.
3. Asigne `chatbot_db` como nombre y `postgres` como propietario; guarde.

## Backend

```powershell
cd TestGroup/django_python/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py import_jira_excel
python manage.py runserver
```

La API queda en `http://127.0.0.1:8000/api/chat/`.

## Verificar PostgreSQL e importar los datos Jira

Con el entorno virtual activado, compruebe la conexión configurada en `backend/.env`:

```powershell
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print(connection.settings_dict['NAME']); print(connection.vendor)"
```

Debe mostrar `chatbot_db` y `postgresql`. La migración crea la tabla `database_jiraissue`; el comando `import_jira_excel` carga los 99 registros de `TestGroup/DATOS_IA_HISTORICO.xlsx`. El comando es idempotente: volver a ejecutarlo actualiza los mismos issues sin duplicarlos.

Para una comprobación posterior de la importación:

```powershell
python manage.py shell -c "from src.database.models import JiraIssue; print(JiraIssue.objects.count())"
```

## Swagger y uso de la API

Inicie Django y abra [Swagger UI](http://127.0.0.1:8000/api/docs/). Allí puede probar los endpoints directamente con **Try it out**. El contrato OpenAPI JSON está disponible en `http://127.0.0.1:8000/api/schema/`.

Prueba rápida de la API desde PowerShell:

```powershell
$body = @{ message = "Analiza los issues de mayor criticidad"; search_filter = "Mayor"; analysis_requested = "Riesgos y estado actual" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/chat/" -ContentType "application/json" -Body $body
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/sessions/"
```

## Frontend

En otra terminal:

```powershell
cd TestGroup/django_python/frontend
npm install
npm run dev
```

Abra la URL que muestre Vite (normalmente `http://localhost:5173`). El archivo `.env` de cada capa contiene los valores locales configurados.

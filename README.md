# ChatBot QA Jira

Aplicacion web interna para analizar calidad de datos Jira (proyecto TATC) mediante un chat, metricas KPI y reportes Word/PDF.

- Backend: Django + Django REST Framework + PostgreSQL (`backend/`).
- Frontend: React + TypeScript + Vite (`frontend/`).
- Las metricas y filtros se calculan en Python. El navegador solo habla con la API Django. No se envian claves de Jira ni de IA al frontend.

Este repositorio no incluye credenciales. Cada persona que lo clone debe crear las suyas.

---

## 1. Requisitos en la maquina

Instala y deja en el PATH:

1. Python 3.11 o superior (`python --version`).
2. Node.js 20 o superior (`node --version` y `npm --version`).
3. PostgreSQL 14 o superior, en ejecucion, con permiso para crear una base de datos.
4. Git.

Opcional, solo si vas a enriquecer reportes con un agente CLI:

- Codex CLI y una clave OpenAI propia (`OPENAI_API_KEY`).
- o Antigravity CLI (`agy`) y una clave Gemini propia (`GEMINI_API_KEY`).

El chat funciona sin esas claves: Python responde con metricas e incidencias. El agente CLI es un paso extra.

---

## 2. Clonar el repositorio

```powershell
git clone <url-del-repositorio>
cd django_python
```

Usa la URL de tu remoto (GitHub u otro). No copies archivos `.env` de otra persona.

---

## 3. Crear la base de datos PostgreSQL

1. Abre pgAdmin (o `psql`) y conéctate con **tu** usuario local. La contraseña es la que definiste al instalar PostgreSQL, no una contraseña publicada en este repo.
2. Crea una base de datos. Nombre sugerido: `chatbot_db`. Propietario: tu usuario (habitualmente `postgres` en Windows).
3. Anota nombre, usuario, contraseña, host (`localhost`) y puerto (`5432`). Los usarás en el paso 5.

Desde `psql`, un ejemplo (cambia usuario y nombre si no coinciden):

```sql
CREATE DATABASE chatbot_db OWNER postgres;
```

---

## 4. Preparar el entorno de desarrollo

En PowerShell, desde la raiz del repositorio:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup-local.ps1
```

En CMD:

```bat
setup-local.bat
```

El script, en orden:

1. Comprueba que existan `python` y `node`.
2. Crea `backend/.venv` si no existe.
3. Instala dependencias de `backend/requirements.txt`.
4. Copia `backend/.env.example` a `backend/.env` si todavía no hay `.env`.
5. Copia `frontend/.env.example` a `frontend/.env` si todavía no hay `.env`.
6. Ejecuta `npm install` en `frontend/`.
7. Intenta `python manage.py migrate`. Si falla, falta completar `backend/.env` o PostgreSQL no está en marcha. Corrige y vuelve a ejecutar el script o el comando de migracion del paso 6.

---

## 5. Configurar tus propias claves (`backend/.env`)

Abre `backend/.env`. Sustituye todos los valores de ejemplo. Nunca subas este archivo a Git.

| Variable | Para que sirve | Donde obtenerla |
|---|---|---|
| `DJANGO_SECRET_KEY` | Firma de Django | Genera una cadena aleatoria larga, unica para tu maquina |
| `JIRA_SERVER` | URL de Jira Cloud | `https://tu-organizacion.atlassian.net` |
| `JIRA_USER` | Cuenta Atlassian | El correo con el que entras a Jira |
| `JIRA_API_TOKEN` | Autenticacion REST | [Create API token](https://id.atlassian.com/manage-profile/security/api-tokens). Crea un token **nuevo**; no reutilices tokens ajenos ni tokens que hayan estado en un chat o README |
| `JIRA_CURRENT_USER` | Filtro "mis tickets" | Normalmente el mismo correo de `JIRA_USER` |
| `JIRA_DATA_SOURCE` | Origen de datos | `jira` para la API real; `local` para la tabla importada |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL | Los datos del paso 3 |
| `AGENT_EXECUTION_MODE` | Como se ejecuta el job | `local` en desarrollo |
| `AGENT_PROVIDER` | Agente CLI opcional | `codex`, `agy` o `mock` (sin CLI) |
| `OPENAI_API_KEY` | Codex CLI | Panel de OpenAI, solo si usas Codex |
| `GEMINI_API_KEY` | Antigravity CLI | Google AI Studio, solo si usas `agy` |

En `frontend/.env` solo debe existir la URL de la API, por ejemplo:

```
VITE_API_URL=http://127.0.0.1:8000/api
```

No pongas tokens de Jira ni de IA en el frontend.

### Si una clave quedo expuesta

`backend/.env` esta en `.gitignore` y no forma parte del historial de este repositorio. Lo que si estuvo versionado es un ejemplo de contraseña de PostgreSQL en documentacion antigua. Si usabas esa contraseña real, cambiala en PostgreSQL y en tu `.env`. Si algun token de Jira, OpenAI o Gemini se copio fuera de tu `.env`, revocalo en el proveedor y genera uno nuevo.

---

## 6. Migrar e importar datos

Con el entorno virtual:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py migrate
```

Comprueba la conexion:

```powershell
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print(connection.settings_dict['NAME']); print(connection.vendor)"
```

Debe mostrar el nombre de tu base y `postgresql`.

### Opcion A: Jira Cloud (recomendado para el chat)

Deja `JIRA_DATA_SOURCE=jira` y completa servidor, usuario y token. El chat lee el proyecto TATC por la API. No hace falta Excel.

### Opcion B: Excel historico (pruebas locales)

1. Pon `JIRA_DATA_SOURCE=local`.
2. Coloca `DATOS_IA_HISTORICO.xlsx` en `TestGroup/` (el directorio padre de este repo) o pasa la ruta:

```powershell
python manage.py import_jira_excel --file "C:\ruta\DATOS_IA_HISTORICO.xlsx"
```

El comando es idempotente: actualiza las mismas claves y no duplica filas.

```powershell
python manage.py shell -c "from src.database.models import JiraIssue; print(JiraIssue.objects.count())"
```

---

## 7. Arrancar la aplicacion

Terminal 1, raiz del repo:

```powershell
.\start-backend.ps1
```

o `start-backend.bat`. La API queda en `http://127.0.0.1:8000/`. Swagger: `http://127.0.0.1:8000/api/docs/`.

Terminal 2:

```powershell
.\start-frontend.ps1
```

o `start-frontend.bat`. Vite suele servir `http://localhost:5173`.

Abre el frontend, escribe una pregunta en espanol (por ejemplo "cuantas incidencias hay", "cuales estan bloqueadas", "informacion del issue TATC-8") y espera la respuesta, las metricas y las pestanas de reporte.

Prueba rapida solo de API:

```powershell
$body = @{ message = "Analiza los issues de mayor criticidad" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/chat/" -ContentType "application/json" -Body $body
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/metrics/"
```

---

## 8. Verificar que todo funciona

Desde `backend/` con `.venv` activo:

```powershell
python manage.py test src.api.tests --keepdb
```

Desde `frontend/`:

```powershell
npm run build
```

La suite cubre sanitizacion, sesiones, metricas, pipeline QA y consultas en lenguaje natural (bloqueos, backlog, en curso, ticket por clave o numero, responsables).

---

## 9. Scripts incluidos

| Archivo | Uso |
|---|---|
| `setup-local.ps1` / `setup-local.bat` | Primera instalacion |
| `start-backend.ps1` / `start-backend.bat` | Django |
| `start-frontend.ps1` / `start-frontend.bat` | Vite |
| `scripts/run_agent_local.ps1` | Harness opcional: baja un issue/Excel y dispara Codex o `agy`. Ejemplo: `.\scripts\run_agent_local.ps1 -Agent codex -IssueKey TATC-8` |

---

## 10. Arquitectura breve

1. El usuario escribe en el chat.
2. `ChatView` valida longitud y escapa HTML.
3. `JiraAgent` detecta intencion y filtros.
4. `fetch_metrics` lee Jira Cloud o PostgreSQL.
5. `run_qa_pipeline` arma la respuesta y las cinco fases del reporte.
6. Si `AGENT_PROVIDER` es `codex` o `agy` y el CLI esta instalado, se puede reescribir el texto del reporte. Si el CLI falla, se conserva el resultado Python.
7. Se generan artefactos Word/PDF y se guarda la sesion.

Secretos: solo `backend/.env`. El JSON de respuesta no incluye tokens.

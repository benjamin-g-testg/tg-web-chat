# Harness opcional de agente CLI. No es necesario para el chat Django.
# Requisitos: backend\.env con JIRA_SERVER/JIRA_USER/JIRA_API_TOKEN propios,
# y OPENAI_API_KEY (codex) o GEMINI_API_KEY (agy) en el mismo archivo o en la sesion.
# Ejemplo:
#   .\scripts\run_agent_local.ps1 -Agent codex -IssueKey TATC-8
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('agy', 'codex')]
    [string]$Agent,

    [string]$IssueKey = $env:ISSUE_KEY
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    foreach ($Line in Get-Content $Path) {
        if ($Line -match '^\s*#' -or $Line -notmatch '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            continue
        }

        $Name = $Matches[1]
        $Value = $Matches[2].Trim()
        if (($Value.StartsWith('"') -and $Value.EndsWith('"')) -or ($Value.StartsWith("'") -and $Value.EndsWith("'"))) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
    }
}

Import-DotEnv (Join-Path $ProjectRoot 'backend\.env')

if (-not $env:JIRA_URL) { $env:JIRA_URL = $env:JIRA_SERVER }
if (-not $env:JIRA_EMAIL) { $env:JIRA_EMAIL = $env:JIRA_USER }

if (-not $IssueKey) {
    throw 'Indica el issue con -IssueKey, por ejemplo -IssueKey TATC-8.'
}
if (-not $env:JIRA_URL -or -not $env:JIRA_EMAIL -or -not $env:JIRA_API_TOKEN) {
    throw 'Faltan JIRA_URL/JIRA_EMAIL/JIRA_API_TOKEN en backend/.env o en la sesión actual.'
}
if ($Agent -eq 'agy' -and -not $env:GEMINI_API_KEY) {
    throw 'Falta GEMINI_API_KEY en la sesión actual de PowerShell.'
}
if ($Agent -eq 'codex' -and -not $env:OPENAI_API_KEY) {
    throw 'Falta OPENAI_API_KEY en la sesión actual de PowerShell.'
}

$env:ISSUE_KEY = $IssueKey
$env:JIRA_URL = $env:JIRA_URL.TrimEnd('/')
$env:OUTPUT_DIR = '02_Datos'

New-Item -ItemType Directory -Force -Path '02_Datos' | Out-Null

@'
import os
from pathlib import Path
import requests
from openpyxl import Workbook

base_url = os.environ['JIRA_URL'].rstrip('/')
issue_key = os.environ['ISSUE_KEY']
auth = (os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN'])
headers = {'Accept': 'application/json'}

response = requests.get(
    f'{base_url}/rest/api/3/issue/{issue_key}?fields=attachment,summary,description,customfield_10166,customfield_10167',
    auth=auth,
    headers=headers,
    timeout=30,
)
response.raise_for_status()
issue = response.json()
fields = issue.get('fields', {})

def extract_text(node):
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        text = node.get('text', '')
        for child in node.get('content', []):
            text += ' ' + extract_text(child)
        return text.strip()
    if isinstance(node, list):
        return ' '.join(extract_text(item) for item in node).strip()
    return ''

analysis_text = extract_text(fields.get('customfield_10166'))
if not analysis_text:
    analysis_text = fields.get('summary', '') or extract_text(fields.get('description'))
if not analysis_text:
    analysis_text = 'Revisa el estado de los Defectos.'

filter_text = extract_text(fields.get('customfield_10167')) or 'Procesa todos los registros.'
Path('03_Info_Complementaria').mkdir(exist_ok=True)
Path('08_Registros_a_Procesar').mkdir(exist_ok=True)
Path('03_Info_Complementaria/Analisis_Particulares.txt').write_text(analysis_text, encoding='utf-8')
Path('08_Registros_a_Procesar/Registros_a_Procesar.txt').write_text(filter_text, encoding='utf-8')
print('Instrucciones del issue sincronizadas en 03_Info_Complementaria y 08_Registros_a_Procesar.')

attachments = fields.get('attachment', [])
excel = next((item for item in attachments if item.get('filename', '').lower().endswith(('.xlsx', '.xls'))), None)

if excel:
    output = Path('02_Datos') / excel['filename']
    download = requests.get(excel['content'], auth=auth, timeout=60)
    download.raise_for_status()
    output.write_bytes(download.content)
    print(f'Excel adjunto descargado: {output}')
    raise SystemExit(0)

issues = []
next_page_token = None
while True:
    payload = {
        'jql': 'project = "TATC" ORDER BY created ASC',
        'maxResults': 100,
        'fields': ['summary', 'status', 'issuetype', 'priority', 'created', 'updated', 'assignee', 'reporter'],
    }
    if next_page_token:
        payload['nextPageToken'] = next_page_token
    page_response = requests.post(
        f'{base_url}/rest/api/3/search/jql',
        auth=auth,
        headers={**headers, 'Content-Type': 'application/json'},
        json=payload,
        timeout=60,
    )
    page_response.raise_for_status()
    page = page_response.json()
    page_issues = page.get('issues', [])
    issues.extend(page_issues)
    next_page_token = page.get('nextPageToken')
    if not next_page_token or not page_issues:
        break

workbook = Workbook()
sheet = workbook.active
sheet.title = 'Resultados_Jira'
sheet.append(['Clave', 'Resumen', 'Tipo', 'Estado', 'Prioridad', 'Asignado', 'Reportador', 'Creado', 'Actualizado'])
for issue in issues:
    fields = issue.get('fields', {})
    sheet.append([
        issue.get('key', ''), fields.get('summary', ''),
        (fields.get('issuetype') or {}).get('name', ''),
        (fields.get('status') or {}).get('name', ''),
        (fields.get('priority') or {}).get('name', ''),
        (fields.get('assignee') or {}).get('displayName', ''),
        (fields.get('reporter') or {}).get('displayName', ''),
        fields.get('created', ''), fields.get('updated', ''),
    ])
output = Path('02_Datos/Jira_Data.xlsx')
workbook.save(output)
print(f'Dataset Jira generado: {output} ({len(issues)} incidencias)')
'@ | python -

$Timestamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$OutputDir = Join-Path '04_Resultado_del_Analisis' $Timestamp
$LogFile = Join-Path '05_Logs' "$Timestamp-$Agent.log"
New-Item -ItemType Directory -Force -Path $OutputDir, '05_Logs' | Out-Null
$EntriesDir = Join-Path $OutputDir 'Entradas'
New-Item -ItemType Directory -Force -Path $EntriesDir | Out-Null

Copy-Item '01_Prompt', '02_Datos', '03_Info_Complementaria', '08_Registros_a_Procesar' -Destination $EntriesDir -Recurse -Force
if (Test-Path '07_Ejemplos') {
    Copy-Item '07_Ejemplos' -Destination $EntriesDir -Recurse -Force
}

$Prompt = @"
Ejecuta el análisis QA de forma eficiente dentro del workspace actual.
Lee 01_Prompt/Prompt_Insights_3_Fases.txt como marco metodológico, sin reproducirlo ni releerlo varias veces.
Usa exclusivamente el dataset de 02_Datos/ y analiza todos sus registros con pandas u openpyxl.
Lee 03_Info_Complementaria/Analisis_Particulares.txt y 08_Registros_a_Procesar/Registros_a_Procesar.txt.
Ejecuta las tres fases obligatorias con hechos, inferencias, recomendaciones, limitaciones y trazabilidad.
Revisa el estado de los Defectos y procesa todos los registros.
Genera en '$OutputDir' los cinco DOCX requeridos, Modelo_utilizado.txt y resumen_respuesta.md.
Usa 07_Ejemplos solo como referencia breve de formato, no como fuente de datos.
Trabaja solo dentro del workspace actual y no uses las rutas Windows antiguas del prompt.
"@

"$Prompt" | Set-Content (Join-Path $OutputDir 'instruccion_local.txt') -Encoding UTF8

if ($Agent -eq 'agy') {
    & agy --model gemini-3.8-flash-low --dangerously-skip-permissions --prompt $Prompt 2>&1 | Tee-Object -FilePath $LogFile
} else {
    $env:CODEX_HOME = Join-Path $ProjectRoot '.codex-harness-local'
    New-Item -ItemType Directory -Force -Path $env:CODEX_HOME | Out-Null
    & codex exec --skip-git-repo-check --sandbox danger-full-access $Prompt 2>&1 | Tee-Object -FilePath $LogFile
}
$AgentResult = $LASTEXITCODE

if (-not (Test-Path (Join-Path $OutputDir 'Modelo_utilizado.txt'))) {
    Set-Content (Join-Path $OutputDir 'Modelo_utilizado.txt') "$Agent`nFecha de ejecución: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding UTF8
}
Compress-Archive -Path (Join-Path $OutputDir '*') -DestinationPath (Join-Path $OutputDir "ZIP_$Agent`_$Timestamp.zip") -Force

Write-Host "Resultado: $AgentResult"
Write-Host "Salida: $OutputDir"
exit $AgentResult
"""Invoke local agents (Codex CLI / Antigravity CLI) with auto-fallback and compact Jira context."""
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any

from django.conf import settings


class LocalAgentError(RuntimeError):
    """Raised when the configured local agent cannot complete the request."""


def run_local_agent_analysis(request: str, context: dict[str, object], output_dir: Path) -> dict[str, str]:
    """
    Ejecuta el agente local configurado (Codex CLI con fallback automático a Antigravity CLI 'agy').
    Si un agente agota su cuota de tokens o no está disponible, conmuta al siguiente automáticamente.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    context_file = output_dir / "contexto_python.json"
    context_file.write_text(json.dumps(context, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    prompt = _build_agent_prompt(request, context_file)

    preferred_provider = getattr(settings, "AGENT_PROVIDER", "codex").lower()
    errors = []

    # 1. Intentar proveedor preferido
    if preferred_provider == "codex":
        try:
            return _execute_codex(prompt, output_dir)
        except Exception as err:
            errors.append(f"Codex: {err}")

        # Fallback a Antigravity CLI (agy)
        try:
            return _execute_agy(prompt, output_dir)
        except Exception as err:
            errors.append(f"Antigravity CLI: {err}")

    elif preferred_provider in ("agy", "antigravity"):
        try:
            return _execute_agy(prompt, output_dir)
        except Exception as err:
            errors.append(f"Antigravity CLI: {err}")

        try:
            return _execute_codex(prompt, output_dir)
        except Exception as err:
            errors.append(f"Codex: {err}")

    raise LocalAgentError(" | ".join(errors) or "No fue posible ejecutar ningún agente local.")


def run_codex_analysis(request: str, context: dict[str, object], output_dir: Path) -> dict[str, str]:
    """Compatibilidad con llamadas existentes."""
    return run_local_agent_analysis(request, context, output_dir)


def _build_agent_prompt(request: str, context_file: Path) -> str:
    return f"""Actúa como analista QA experto y responde en español.
La consulta del usuario es: {request}

Python ya consultó Jira, aplicó el alcance solicitado y calculó las métricas deterministas.
Lee únicamente el contexto preparado en: {context_file}
No consultes Jira externamente, no inventes datos y distingue evidencia, interpretación y recomendación.
Responde directamente la consulta usando únicamente las incidencias de `selected_issues` del contexto.
El responsable se informa individualmente por issue usando `assignee`. Si no tiene, escribe "Sin responsable".

Devuelve únicamente un objeto JSON válido, sin Markdown ni bloques de código adicionales, con exactamente estas claves:
chat_response (respuesta directa y contextualizada para el chat, máximo 500 caracteres),
phase_1 (perfil y evidencia de los datos),
phase_2 (hallazgos e insights prioritarios),
phase_3 (respuesta detallada y concreta a la consulta),
conclusion (conclusión y recomendaciones clave),
executive_summary (resumen ejecutivo de alto nivel).
"""


def _execute_codex(prompt: str, output_dir: Path) -> dict[str, str]:
    executable = shutil.which("codex.ps1") or shutil.which("codex") or shutil.which("codex.cmd")
    if not executable:
        raise LocalAgentError("No se encontró Codex CLI en PATH.")

    if executable.lower().endswith(".ps1"):
        command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", executable,
            "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
            "--cd", str(Path(settings.BASE_DIR).parent), "-",
        ]
    else:
        command = [
            executable, "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
            "--cd", str(Path(settings.BASE_DIR).parent), "-",
        ]

    timeout = int(getattr(settings, "AGENT_TIMEOUT", 120))
    try:
        result = subprocess.run(
            command,
            cwd=Path(settings.BASE_DIR).parent,
            capture_output=True,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise LocalAgentError(f"Codex superó el timeout de {timeout}s.") from error

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Error desconocido").strip()
        raise LocalAgentError(f"Codex terminó con código {result.returncode}: {detail[-400:]}")

    raw_output = result.stdout.strip()
    (output_dir / "respuesta_codex.txt").write_text(raw_output, encoding="utf-8")
    return _parse_agent_json(raw_output)


def _execute_agy(prompt: str, output_dir: Path) -> dict[str, str]:
    executable = shutil.which("agy.cmd") or shutil.which("agy") or shutil.which("agy.ps1")
    if not executable:
        raise LocalAgentError("No se encontró Antigravity CLI (agy) en PATH.")

    command = [
        executable,
        "--model", "gemini-2.5-flash",
        "--dangerously-skip-permissions",
        "--prompt", prompt,
    ]

    timeout = int(getattr(settings, "AGENT_TIMEOUT", 120))
    try:
        result = subprocess.run(
            command,
            cwd=Path(settings.BASE_DIR).parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise LocalAgentError(f"Antigravity CLI superó el timeout de {timeout}s.") from error

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Error desconocido").strip()
        raise LocalAgentError(f"Antigravity CLI terminó con código {result.returncode}: {detail[-400:]}")

    raw_output = result.stdout.strip()
    (output_dir / "respuesta_agy.txt").write_text(raw_output, encoding="utf-8")
    return _parse_agent_json(raw_output)


def _parse_agent_json(raw_output: str) -> dict[str, str]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(raw_output):
        if character != "{":
            continue
        try:
            parsed = decoder.raw_decode(raw_output[index:])[0]
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            required = {"chat_response", "phase_1", "phase_2", "phase_3", "conclusion", "executive_summary"}
            if required.issubset(parsed):
                return {key: _report_text(parsed[key]) for key in required}

    if raw_output:
        return {
            "chat_response": raw_output[:500],
            "phase_1": "",
            "phase_2": "",
            "phase_3": raw_output,
            "conclusion": raw_output,
            "executive_summary": raw_output,
        }

    raise LocalAgentError("El agente no devolvió contenido para el reporte.")


def _report_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        sections = []
        for key, item in value.items():
            label = str(key).replace("_", " ").capitalize()
            if isinstance(item, list):
                sections.append(f"{label}:\n" + "\n".join(f"- {entry}" for entry in item))
            else:
                sections.append(f"{label}: {item}")
        return "\n".join(sections)
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    return str(value)
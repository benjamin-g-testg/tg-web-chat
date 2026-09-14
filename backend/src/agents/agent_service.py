"""
JiraAgent: Interpreta comandos del usuario y ejecuta acciones en Jira.
Soporta comandos para lectura, filtrado dinamico, creacion de reportes y exportacion de datos.
"""
import re
import unicodedata
from difflib import get_close_matches
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class IntentType(Enum):
    """Tipos de intencion que puede detectar el agente."""
    LIST_BLOCKED = "list_blocked"
    LIST_BY_STATUS = "list_by_status"
    CREATE_REPORT = "create_report"
    EXPORT_EXCEL = "export_excel"
    FILTER_ISSUES = "filter_issues"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"


@dataclass
class AgentResponse:
    """Estructura de respuesta del agente despues de procesar un mensaje."""
    intent: IntentType
    action: str
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    error: Optional[str] = None


class JiraAgent:
    """Agente que interpreta mensajes en lenguaje natural y genera intenciones estructuradas."""

    def __init__(self):
        """Inicializa los patrones de deteccion de intencion."""
        self.intent_patterns = {
            IntentType.LIST_BLOCKED: [
                r"(bloqueados?|bloqueante|bloqueos?|bloqueadas?)",
                r"(stuck|blocked|blocking)",
            ],
            IntentType.LIST_BY_STATUS: [
                r"(en curso|in progress|progreso)",
                r"(backlog|por hacer|todo|pendientes?)",
                r"(terminado|done|completado|cerrado|resuelto)",
            ],
            IntentType.CREATE_REPORT: [
                r"(reporte|report|analisis|analysis|resumen)",
                r"(summary|estadisticas|stats|metricas)",
            ],
            IntentType.EXPORT_EXCEL: [
                r"(exporta?r?|export).*(excel|xlsx)",
                r"(descarga?r?|download).*excel",
            ],
            IntentType.FILTER_ISSUES: [
                r"(filtr[ao]|filter|busca?r?|search)",
            ],
        }

    def detect_intent(self, message: str) -> IntentType:
        """Detecta la intencion principal del mensaje usando patrones regex normalizados."""
        if not message:
            return IntentType.UNKNOWN

        message_lower = normalize_text(message)

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, message_lower):
                        return intent
                except re.error:
                    continue

        return IntentType.UNKNOWN

    def process_message(self, message: str) -> AgentResponse:
        """
        Procesa el mensaje del usuario y construye la respuesta estructurada de la intencion.
        """
        if not message or len(message) > 5000:
            return AgentResponse(
                intent=IntentType.UNKNOWN,
                action="error",
                error="Mensaje invalido o excede el limite de caracteres.",
            )

        normalized = normalize_text(message)
        intent = self.detect_intent(normalized)
        status = extract_status(normalized)

        filters: Dict[str, Any] = {}
        if status:
            filters["status_category"] = status

        key_match = re.search(r"\b([a-z]+-\d+)\b", normalized)
        if key_match:
            filters["issue_key"] = key_match.group(1).upper()

        numeric_match = re.search(
            r"\b(?:issue|issues|ticket|tickets|caso|casos)\s*(?:numero\s*)?#?\s*(\d+)\b",
            normalized,
        )
        if numeric_match and "issue_key" not in filters:
            filters["issue_key"] = f"TATC-{numeric_match.group(1)}"

        if re.search(r"\b(asignad[oa]s?|responsable|dueno|duena|encargad[oa]|owner)\b", normalized) and re.search(r"\b(a\s+mi|mis|mios|mias|yo)\b", normalized):
            filters["assignee_me"] = True

        assignee_match = re.search(
            r"\b(?:asignad[oa]s?|responsable|dueno|duena|encargad[oa]|owner)\s+(?:a\s+)?([a-z][\w .'-]{2,})",
            normalized,
        )
        if assignee_match and not filters.get("assignee_me"):
            candidate = assignee_match.group(1).strip(" .,'\"")
            candidate = re.split(r"\s+(?:en|con|de|del|que|y)\s+", candidate, maxsplit=1)[0]
            if candidate:
                filters["assignee"] = candidate

        limit_match = re.search(r"\b(?:los|las|primeros|primeras)\s+(\d+)\b", normalized)
        data: Dict[str, Any] = {"filters": filters, "normalized_query": normalized}
        if limit_match:
            data["limit"] = int(limit_match.group(1))

        if intent == IntentType.LIST_BLOCKED:
            response = AgentResponse(
                intent=IntentType.LIST_BLOCKED,
                action="list_blocked",
                message="Buscando incidencias con bloqueo o criticidad bloqueante en el proyecto TATC.",
            )
        elif intent == IntentType.LIST_BY_STATUS:
            category = status or "desconocido"
            response = AgentResponse(
                intent=IntentType.LIST_BY_STATUS,
                action="list_by_status",
                data={"status": status, "category": category},
                message=f"Filtrando incidencias bajo categoria '{category}'.",
            )
        elif intent == IntentType.CREATE_REPORT:
            response = AgentResponse(
                intent=IntentType.CREATE_REPORT,
                action="run_qa_pipeline",
                message="Generando reporte integral de analisis QA.",
            )
        elif intent == IntentType.EXPORT_EXCEL:
            response = AgentResponse(
                intent=IntentType.EXPORT_EXCEL,
                action="export_excel",
                message="Preparando dataset para exportacion Excel.",
            )
        elif intent == IntentType.FILTER_ISSUES:
            filter_term = self._extract_filter(normalized)
            response = AgentResponse(
                intent=IntentType.FILTER_ISSUES,
                action="filter_issues",
                data={"filter": filter_term},
                message=f"Filtrando incidencias por criterio: '{filter_term}'.",
            )
        else:
            response = AgentResponse(
                intent=IntentType.GENERAL_QUERY,
                action="run_qa_pipeline",
                message="Consulta general procesada por pipeline QA.",
            )

        response.data = {**data, **(response.data or {})}
        return response

    def _extract_filter(self, message: str) -> str:
        """Extrae termino o criterio de busqueda de un mensaje."""
        match = re.search(r'"([^"]+)"', message)
        if match:
            return match.group(1)

        match = re.search(r"(?:filtro|filter|buscar|search)\s+(.+)", message, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""


def normalize_text(value: str) -> str:
    """Normaliza texto eliminando acentos, estandarizando espacios y convirtiendo a minusculas."""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn")
    value = re.sub(r"[^\w\s#-]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def extract_status(message: str) -> str:
    """Mapea terminos y sinonimos de estado a categorias globales nativas de Jira."""
    normalized = normalize_text(message)
    aliases = {
        "done": "done",
        "terminado": "done",
        "terminados": "done",
        "completado": "done",
        "completados": "done",
        "cerrado": "done",
        "cerrados": "done",
        "resuelto": "done",
        "resueltos": "done",
        "en curso": "indeterminate",
        "in progress": "indeterminate",
        "progreso": "indeterminate",
        "backlog": "new",
        "por hacer": "new",
        "pendiente": "new",
        "pendientes": "new",
        "nuevo": "new",
        "nuevos": "new",
        "nueva": "new",
        "nuevas": "new",
        "bloqueado": "blocked",
        "bloqueados": "blocked",
        "bloqueante": "blocked",
        "blocked": "blocked",
    }
    for alias, category in aliases.items():
        if alias in normalized:
            return category
    words = normalized.split()
    known = list(aliases)
    for word in words:
        match = get_close_matches(word, known, n=1, cutoff=0.82)
        if match:
            return aliases[match[0]]
    return ""

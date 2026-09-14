"""
JiraAgent: Interpreta comandos del usuario y ejecuta acciones en Jira.
Soporta comandos para leer, filtrar, crear reportes y exportar datos.

Phase 2: Agentes inteligentes basados en intención de usuario.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any


class IntentType(Enum):
    """Tipos de intención que puede detectar el agente"""
    LIST_BLOCKED = "list_blocked"
    LIST_BY_STATUS = "list_by_status"
    CREATE_REPORT = "create_report"
    EXPORT_EXCEL = "export_excel"
    FILTER_ISSUES = "filter_issues"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"


@dataclass
class AgentResponse:
    """Respuesta del agente después de procesar un mensaje"""
    intent: IntentType
    action: str
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    error: Optional[str] = None


class JiraAgent:
    """Agente que interpreta mensajes y ejecuta acciones en Jira"""
    
    def __init__(self):
        """Inicializa el agente con patrones de intención"""
        self.intent_patterns = {
            IntentType.LIST_BLOCKED: [
                r"(bloqueados?|bloqueante|bloqueos?|bloqueadas?)",
                r"(stuck|blocked|blocking)",
            ],
            IntentType.LIST_BY_STATUS: [
                r"(en curso|in progress|progreso)",
                r"(backlog|por hacer|todo)",
                r"(terminado|done|completado|cerrado)",
            ],
            IntentType.CREATE_REPORT: [
                r"(reporte|report|análisis|analysis|resumen)",
                r"(summary|estadísticas|stats)",
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
        """Detecta la intención del mensaje usando regex"""
        if not message:
            return IntentType.UNKNOWN
        
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, message_lower):
                        return intent
                except re.error:
                    # Si hay error en regex, continuar con siguiente patrón
                    continue
        
        return IntentType.UNKNOWN
    
    def process_message(self, message: str) -> AgentResponse:
        """
        Procesa mensaje y retorna acción a ejecutar.
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            AgentResponse con intención detectada y acción a ejecutar
        """
        
        if not message or len(message) > 5000:
            return AgentResponse(
                intent=IntentType.UNKNOWN,
                action="error",
                error="Mensaje inválido o muy largo"
            )
        
        intent = self.detect_intent(message)
        
        if intent == IntentType.LIST_BLOCKED:
            return self._handle_list_blocked()
        
        elif intent == IntentType.LIST_BY_STATUS:
            status = self._extract_status(message)
            return self._handle_list_by_status(status)
        
        elif intent == IntentType.CREATE_REPORT:
            return self._handle_create_report(message)
        
        elif intent == IntentType.EXPORT_EXCEL:
            return self._handle_export_excel(message)
        
        elif intent == IntentType.FILTER_ISSUES:
            filter_term = self._extract_filter(message)
            return self._handle_filter_issues(filter_term)
        
        else:
            return AgentResponse(
                intent=IntentType.GENERAL_QUERY,
                action="run_qa_pipeline",
                message="Consulta general procesada por pipeline QA"
            )
    
    def _handle_list_blocked(self) -> AgentResponse:
        """Listar issues bloqueados"""
        return AgentResponse(
            intent=IntentType.LIST_BLOCKED,
            action="list_blocked",
            message="Buscando issues bloqueados en el proyecto TATC..."
        )
    
    def _handle_list_by_status(self, status: str) -> AgentResponse:
        """Listar issues por estado"""
        status_map = {
            "bloqueado": "done",
            "terminado": "done",
            "en curso": "indeterminate",
            "progreso": "indeterminate",
            "backlog": "new",
            "por hacer": "new",
        }
        
        category = status_map.get(status.lower(), status)
        
        return AgentResponse(
            intent=IntentType.LIST_BY_STATUS,
            action="list_by_status",
            data={"status": status, "category": category},
            message=f"Filtrando issues en estado '{status}'..."
        )
    
    def _handle_create_report(self, message: str) -> AgentResponse:
        """Crear reporte de análisis"""
        return AgentResponse(
            intent=IntentType.CREATE_REPORT,
            action="run_qa_pipeline",
            message="Generando reporte de análisis QA..."
        )
    
    def _handle_export_excel(self, message: str) -> AgentResponse:
        """Exportar datos a Excel"""
        return AgentResponse(
            intent=IntentType.EXPORT_EXCEL,
            action="export_excel",
            message="Preparando descarga de Excel..."
        )
    
    def _handle_filter_issues(self, filter_term: str) -> AgentResponse:
        """Filtrar issues por término"""
        return AgentResponse(
            intent=IntentType.FILTER_ISSUES,
            action="filter_issues",
            data={"filter": filter_term},
            message=f"Filtrando issues por: '{filter_term}'"
        )
    
    def _extract_status(self, message: str) -> str:
        """Extrae estado del mensaje"""
        status_keywords = {
            "bloqueado": "bloqueado",
            "terminado": "terminado",
            "en curso": "en curso",
            "progreso": "en curso",
            "backlog": "backlog",
            "por hacer": "backlog",
            "done": "terminado",
        }
        
        message_lower = message.lower()
        for keyword in status_keywords:
            if keyword in message_lower:
                return keyword
        
        return "desconocido"
    
    def _extract_filter(self, message: str) -> str:
        """Extrae término de filtro del mensaje"""
        # Busca texto entre comillas
        match = re.search(r'"([^"]+)"', message)
        if match:
            return match.group(1)
        
        # Si no hay comillas, toma el resto después de palabra clave
        match = re.search(
            r'(?:filtro|filter|buscar|search)\s+(.+)',
            message,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        
        return ""

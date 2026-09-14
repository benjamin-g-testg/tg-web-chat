"""Business service that runs the deterministic three-stage QA pipeline with tailored natural language generation."""
from typing import Any
import re
from src.integrations.jira_client import fetch_metrics, JiraMetrics
from src.agents.agent_service import normalize_text


def run_qa_pipeline(
    message: str,
    search_filter: str,
    analysis_requested: str,
    filters: dict[str, object] | None = None,
) -> dict[str, Any]:
    filters = filters or {}
    metrics: JiraMetrics = fetch_metrics(
        search_filter,
        exclude_subtasks=False,
        include_debug=True,
        filters=filters,
    )

    total = metrics.total
    completed = metrics.completed
    in_progress = metrics.in_progress
    blocked = metrics.blocked
    new_count = metrics.new
    status_dist = metrics.status_distribution or {}
    completion_rate = round(completed / total * 100, 2) if total else 0.0

    scope = search_filter or "alcance general del proyecto TATC"
    request = analysis_requested or message
    issues = metrics.issues_found or []

    # Generación dinámica y contextualizada de la respuesta y fases
    chat_response = _synthesize_chat_response(message, metrics, issues, filters)
    phase_1 = _generate_phase_1(scope, metrics, issues)
    phase_2 = _generate_phase_2(metrics, issues, completion_rate)
    phase_3 = _generate_phase_3(request, metrics, issues, filters)
    conclusion = _generate_conclusion(metrics, completion_rate)
    executive_summary = _generate_executive_summary(metrics, completion_rate)

    reports = {
        "phase_1": phase_1,
        "phase_2": phase_2,
        "phase_3": phase_3,
        "conclusion": conclusion,
        "executive_summary": executive_summary,
    }

    return {
        "chat_response": chat_response,
        "reports": reports,
        "metrics": {
            **metrics.to_dict(),
            "total_issues": total,
            "blocked_issues": blocked,
            "completion_rate": completion_rate,
        },
        "agent_context": {
            "request": request,
            "search_filter": scope,
            "filters": filters,
            "metrics": metrics.to_dict(include_debug=False),
            "issues": issues,
            "selected_issues": issues,
            "selected_count": len(issues),
        },
    }


def _synthesize_chat_response(
    message: str,
    metrics: JiraMetrics,
    issues: list[dict[str, Any]],
    filters: dict[str, Any],
) -> str:
    """Sintetiza una respuesta conversacional directa, específica y fundamentada en la pregunta."""
    query_norm = normalize_text(message)

    # 1. Consulta por un issue específico (e.g. TATC-8 o #8)
    if filters.get("issue_key") and issues:
        target = issues[0]
        assignee = target.get("assignee") or "Sin responsable asignado"
        status = target.get("status", "Sin estado")
        summary = target.get("summary", "")
        priority = target.get("priority", "No definida")
        issue_type = target.get("type", "Tarea")
        blocked_text = " (Presenta BLOQUEO)" if target.get("blocked") else ""
        return (
            f"Información de la incidencia {target.get('key', '')}:\n"
            f"• Resumen: {summary}\n"
            f"• Estado: {status}{blocked_text}\n"
            f"• Responsable: {assignee}\n"
            f"• Tipo: {issue_type} | Prioridad: {priority}"
        )

    # 2. Consulta sobre issues completados / de qué tratan / quién está a cargo
    if any(term in query_norm for term in ["completad", "terminad", "done", "cerrad", "resuelt"]):
        completed_issues = [
            i for i in issues if i.get("category") == "done" or "termino" in str(i.get("status", "")).lower()
        ]
        if not completed_issues:
            return "No se encontraron incidencias en estado completado en el alcance evaluado."

        # Si preguntan por quién está a cargo / asignados
        if any(term in query_norm for term in ["cargo", "responsable", "dueno", "quien", "asignad"]):
            lines = [f"Actualmente hay {len(completed_issues)} incidencias completadas con los siguientes responsables:"]
            for item in completed_issues:
                assignee = item.get("assignee") or "Sin responsable asignado"
                lines.append(f"• {item.get('key', '')}: {assignee} (Estado: {item.get('status', '')})")
            return "\n".join(lines)

        # Si preguntan de qué tratan o listado
        lines = [
            f"Se registran {len(completed_issues)} incidencias completadas en el proyecto:"
        ]
        successful = [i for i in completed_issues if "exitoso" in str(i.get("status", "")).lower()]
        failed = [i for i in completed_issues if "fallido" in str(i.get("status", "")).lower()]
        other = [i for i in completed_issues if i not in successful and i not in failed]

        if successful:
            lines.append(f"\nCon Término Exitoso ({len(successful)}):")
            for item in successful:
                assignee = f" (Asignado: {item.get('assignee')})" if item.get("assignee") else ""
                lines.append(f"• {item.get('key', '')}: {item.get('summary', '')[:90]}{assignee}")

        if failed:
            lines.append(f"\nCon Término Fallido ({len(failed)}):")
            for item in failed:
                assignee = f" (Asignado: {item.get('assignee')})" if item.get("assignee") else ""
                lines.append(f"• {item.get('key', '')}: {item.get('summary', '')[:90]}{assignee}")

        if other:
            lines.append("\nOtras finalizadas:")
            for item in other:
                lines.append(f"• {item.get('key', '')}: {item.get('summary', '')[:90]} ({item.get('status', '')})")

        return "\n".join(lines)

    # 3. Consulta sobre issues en progreso / en curso
    if any(term in query_norm for term in ["progreso", "en curso", "in progress"]):
        in_prog_issues = [
            i for i in issues if i.get("category") == "indeterminate" or "curso" in str(i.get("status", "")).lower()
        ]
        if not in_prog_issues:
            return "Actualmente no se registran incidencias en estado 'En curso' o 'En progreso'."
        lines = [f"Se registra {len(in_prog_issues)} incidencia(s) actualmente en progreso:"]
        for item in in_prog_issues:
            assignee = item.get("assignee") or "Sin responsable asignado"
            lines.append(
                f"• {item.get('key', '')}: {item.get('summary', '')}\n"
                f"  └─ Estado: {item.get('status', '')} | Responsable: {assignee} | Prioridad: {item.get('priority', 'Media')}"
            )
        return "\n".join(lines)

    # 4. Consulta sobre Backlog / Pendientes / Nuevos
    if any(term in query_norm for term in ["backlog", "pendiente", "por hacer", "nuev"]):
        backlog_issues = [
            i for i in issues if i.get("category") == "new" or "backlog" in str(i.get("status", "")).lower()
        ]
        if not backlog_issues:
            return "No se encontraron incidencias pendientes en el Backlog dentro del alcance seleccionado."
        lines = [f"Existen {len(backlog_issues)} incidencias en el Backlog / pendientes:"]
        for item in backlog_issues:
            assignee = item.get("assignee") or "Sin responsable"
            lines.append(f"• {item.get('key', '')}: {item.get('summary', '')[:90]} (Estado: {item.get('status', '')}, Responsable: {assignee})")
        return "\n".join(lines)

    # 5. Consulta sobre Bloqueos
    if any(term in query_norm for term in ["bloque", "stuck", "impediment"]):
        blocked_issues = [i for i in issues if i.get("blocked")]
        if not blocked_issues:
            return "Excelente noticia: No se detectan incidencias con bloqueo activo ni criticidad bloqueante en este alcance."
        lines = [f"Atención: Se detectaron {len(blocked_issues)} incidencias bloqueadas que requieren intervención inmediata:"]
        for item in blocked_issues:
            assignee = item.get("assignee") or "Sin responsable"
            lines.append(f"• {item.get('key', '')}: {item.get('summary', '')} (Estado: {item.get('status', '')}, Responsable: {assignee})")
        return "\n".join(lines)

    # 6. Consulta general sobre inventario de incidencias o métricas totales
    dist_str = ", ".join(f"{k}: {v}" for k, v in (metrics.status_distribution or {}).items())
    return (
        f"Actualmente existen {metrics.total} incidencias registradas en el proyecto TATC.\n\n"
        f"• Distribución por estado: {dist_str or 'Sin distribución'}\n"
        f"• Completados: {metrics.completed} ({round(metrics.completed / metrics.total * 100, 1) if metrics.total else 0}%)\n"
        f"• En progreso: {metrics.in_progress}\n"
        f"• Bloqueados: {metrics.blocked}\n"
        f"• Backlog / Nuevos: {metrics.new}\n\n"
        f"Para un desglose detallado por fases, revise las pestañas inferiores o descargue los reportes formales en Word o PDF."
    )


def _generate_phase_1(scope: str, metrics: JiraMetrics, issues: list[dict[str, Any]]) -> str:
    """Fase 1: Perfil y evidencia de calidad de datos."""
    total = metrics.total
    with_assignee = sum(bool(i.get("assignee")) for i in issues)
    no_assignee = total - with_assignee
    dist_items = [f"- {k}: {v} incidencia(s)" for k, v in (metrics.status_distribution or {}).items()]
    dist_str = "\n".join(dist_items) if dist_items else "- Sin datos de distribución"

    return (
        f"1. ALCANCE Y CONTEXTO:\n"
        f"Se realizó la inspección de calidad sobre {total} incidencias del proyecto TATC ({scope}).\n\n"
        f"2. INTEGRIDAD Y CLASIFICACIÓN DE ESTADOS:\n"
        f"La categoría global nativa de Jira agrupa los flujos de trabajo en: {metrics.completed} finalizados (Done), {metrics.in_progress} en curso (Indeterminate) y {metrics.new} en estado inicial (New).\n"
        f"Distribución real observada en los registros:\n{dist_str}\n\n"
        f"3. TRAZABILIDAD Y ASIGNACIÓN:\n"
        f"- Incidencias con responsable identificado: {with_assignee} ({round(with_assignee/total*100, 1) if total else 0}%)\n"
        f"- Incidencias sin responsable asignado: {no_assignee}\n"
        f"- Detección de bloqueos explícitos o criticidad bloqueante: {metrics.blocked} incidencia(s)."
    )


def _generate_phase_2(metrics: JiraMetrics, issues: list[dict[str, Any]], completion_rate: float) -> str:
    """Fase 2: Hallazgos e insights de calidad y avance."""
    successful = sum(1 for i in issues if "exitoso" in str(i.get("status", "")).lower())
    failed = sum(1 for i in issues if "fallido" in str(i.get("status", "")).lower())

    findings = [
        f"1. RENDIMIENTO DEL FLUJO:\n"
        f"La tasa global de completitud se sitúa en {completion_rate}%. De las {metrics.completed} incidencias cerradas, {successful} alcanzaron un término exitoso y {failed} registraron término fallido, lo cual requiere auditoría de causas raíz en el aseguramiento de calidad.",
    ]

    if metrics.blocked > 0:
        findings.append(
            f"2. RIESGO POR BLOQUEOS:\n"
            f"Existen {metrics.blocked} incidencia(s) detenidas. Es crítico convocar a los líderes técnicos y dueños de producto para desbloquear dependencias externas."
        )
    else:
        findings.append(
            "2. CONTINUIDAD OPERATIVA:\n"
            "No se registran bloqueos activos en el pipeline, lo que permite una ejecución fluida de las tareas en curso."
        )

    findings.append(
        f"3. CAPACIDAD Y BACKLOG:\n"
        f"Con {metrics.in_progress} ticket(s) en desarrollo activo y {metrics.new} en Backlog, se recomienda balancear la asignación de carga de trabajo para evitar cuellos de botella en la fase de certificación."
    )

    return "\n\n".join(findings)


def _generate_phase_3(
    request: str,
    metrics: JiraMetrics,
    issues: list[dict[str, Any]],
    filters: dict[str, Any],
) -> str:
    """Fase 3: Respuesta concreta y técnica a la consulta formulada."""
    synthesis = _synthesize_chat_response(request, metrics, issues, filters)
    return (
        f"RESPUESTA ESPECÍFICA A LA CONSULTA:\n"
        f"“{request}”\n\n"
        f"{synthesis}\n\n"
        f"EVIDENCIA ASOCIADA:\n"
        f"Se validó la totalidad de los {metrics.total} registros coincidentes mediante el cliente unificado de Jira, garantizando consistencia y trazabilidad en los resultados informados."
    )


def _generate_conclusion(metrics: JiraMetrics, completion_rate: float) -> str:
    """Conclusión y recomendaciones estratégicas."""
    risk_level = "Alto" if metrics.blocked > 2 else ("Moderado" if metrics.blocked > 0 or completion_rate < 50 else "Bajo")

    return (
        f"1. EVALUACIÓN GENERAL:\n"
        f"El proyecto presenta un nivel de riesgo {risk_level} con un avance del {completion_rate}% sobre {metrics.total} incidencias evaluadas.\n\n"
        f"2. RECOMENDACIONES CLAVE:\n"
        f"• Asegurar que todas las incidencias en curso ({metrics.in_progress}) cuenten con criterios de aceptación definidos y casos de prueba automatizados.\n"
        f"• Asignar responsables explícitos a todos los elementos del Backlog antes de la próxima planificación.\n"
        f"• Realizar seguimiento diario a los defectos para reducir el tiempo medio de resolución (MTTR)."
    )


def _generate_executive_summary(metrics: JiraMetrics, completion_rate: float) -> str:
    """Resumen Ejecutivo para directores y partes interesadas."""
    dist_str = ", ".join(f"{k}: {v}" for k, v in (metrics.status_distribution or {}).items())
    return (
        f"RESUMEN EJECUTIVO DE CALIDAD JIRA\n\n"
        f"• Total Incidencias Analizadas: {metrics.total}\n"
        f"• Tasa de Finalización: {completion_rate}%\n"
        f"• Incidencias Completadas: {metrics.completed}\n"
        f"• Incidencias en Progreso: {metrics.in_progress}\n"
        f"• Incidencias Bloqueadas: {metrics.blocked}\n"
        f"• Distribución de Estados: {dist_str or 'N/A'}\n\n"
        f"Acción Inmediata: Validar entregables del sprint, revisar incidencias con término fallido y asegurar cobertura de pruebas antes del paso a producción."
    )

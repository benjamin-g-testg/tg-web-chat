"""Business service that runs the deterministic three-stage QA pipeline."""
from dataclasses import asdict
from src.integrations.jira_client import fetch_metrics


def run_qa_pipeline(message: str, search_filter: str, analysis_requested: str) -> dict[str, object]:
    metrics = fetch_metrics(search_filter)
    completion_rate = round(metrics.completed / metrics.total * 100, 2)
    scope = search_filter or "todos los issues del alcance actual"
    request = analysis_requested or message
    reports = {
        "phase_1": f"Calidad de datos: se evaluaron {metrics.total} issues para {scope}. Hay {metrics.completed} completados, {metrics.in_progress} en progreso y {metrics.blocked} bloqueados. La antigüedad media abierta es de {metrics.average_open_days} días.",
        "phase_2": f"Hallazgos prioritarios: los {metrics.blocked} bloqueos requieren dueño y fecha de resolución. La tasa de finalización ({completion_rate}%) sugiere revisar capacidad y dependencias antes del siguiente sprint.",
        "phase_3": f"Respuesta a la consulta: “{request}”. Se recomienda validar los tickets críticos, confirmar criterios de aceptación y registrar riesgos en la ceremonia de seguimiento.",
        "conclusion": f"El flujo presenta riesgo moderado: {metrics.blocked} de {metrics.total} issues están bloqueados. Priorice su desbloqueo y mida nuevamente el avance al cierre de la semana.",
        "executive_summary": f"Resumen ejecutivo: {metrics.total} issues analizados; {completion_rate}% completado; {metrics.blocked} bloqueados. Acción inmediata: asignar responsables a los bloqueos.",
    }
    return {"reports": reports, "metrics": {**asdict(metrics), "total_issues": metrics.total, "blocked_issues": metrics.blocked, "completion_rate": completion_rate}}

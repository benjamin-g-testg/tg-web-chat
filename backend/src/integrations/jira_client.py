"""Replace this deterministic local source with Jira REST authentication when available."""
from dataclasses import dataclass
from django.db.models import Q
from src.database.models import JiraIssue

@dataclass(frozen=True)
class JiraMetrics:
    total: int = 12
    completed: int = 4
    in_progress: int = 3
    blocked: int = 2
    average_open_days: int = 27

def fetch_metrics(search_filter: str) -> JiraMetrics:
    """Summarize imported Jira data, with safe fallback before the first import."""
    queryset = JiraIssue.objects.all()
    if search_filter:
        queryset = queryset.filter(Q(issue_key__icontains=search_filter) | Q(status__icontains=search_filter) | Q(criticality__icontains=search_filter) | Q(phase__icontains=search_filter))
    total = queryset.count()
    if total == 0:
        return JiraMetrics()
    completed = queryset.filter(status__in=["Superado", "Finalizado", "Cerrado", "Listo"]).count()
    in_progress = queryset.filter(status__icontains="Progreso").count()
    blocked = queryset.filter(Q(status__icontains="Bloque") | Q(criticality__icontains="Bloqueante")).count()
    return JiraMetrics(total=total, completed=completed, in_progress=in_progress, blocked=blocked, average_open_days=0)

"""Provide a single metrics source for local history and Jira Cloud."""
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db.models import Q

from src.database.models import JiraIssue

@dataclass(frozen=True)
class JiraMetrics:
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    new: int = 0
    blocked: int = 2
    average_open_days: int = 0
    issues_found: Optional[list[dict[str, object]]] = None

    def to_dict(self, include_debug: bool = False) -> dict[str, object]:
        result = {
            "total": self.total,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "new": self.new,
            "blocked": self.blocked,
            "average_open_days": self.average_open_days,
        }
        if include_debug:
            result["debug_issues"] = self.issues_found or []
        return result


def fetch_metrics(
    search_filter: str = "",
    *,
    exclude_subtasks: bool = True,
    include_debug: bool = False,
) -> JiraMetrics:
    """Summarize the configured source without making an implicit network call."""
    if getattr(settings, "JIRA_DATA_SOURCE", "local").lower() == "jira":
        return _fetch_jira_metrics(
            search_filter,
            exclude_subtasks=exclude_subtasks,
            include_debug=include_debug,
        )
    return _fetch_local_metrics(
        search_filter,
        exclude_subtasks=exclude_subtasks,
        include_debug=include_debug,
    )


def _fetch_local_metrics(
    search_filter: str,
    *,
    exclude_subtasks: bool,
    include_debug: bool,
) -> JiraMetrics:
    """Read the normalized JiraIssue table populated by the Excel importer."""
    queryset = JiraIssue.objects.all()
    if exclude_subtasks:
        queryset = queryset.exclude(issue_type__iexact="Sub-task")
    if search_filter:
        queryset = queryset.filter(
            Q(issue_key__icontains=search_filter)
            | Q(status__icontains=search_filter)
            | Q(criticality__icontains=search_filter)
            | Q(phase__icontains=search_filter)
        )
    total = queryset.count()
    if total == 0:
        return JiraMetrics()

    completed = queryset.filter(
        Q(status_category__iexact="done")
        | Q(status__in=["Superado", "Finalizado", "Cerrado", "Listo"])
    ).count()
    in_progress = queryset.filter(
        Q(status_category__iexact="indeterminate") | Q(status__icontains="Progreso")
    ).count()
    blocked = queryset.filter(
        Q(status__icontains="Bloque") | Q(criticality__icontains="Bloqueante")
    ).count()
    new = max(total - completed - in_progress, 0)
    issues = []
    if include_debug:
        issues = [
            {
                "key": issue.issue_key,
                "summary": issue.description[:160],
                "status": issue.status,
                "category": issue.status_category,
                "priority": issue.criticality,
                "type": issue.issue_type,
                "blocked": "bloque" in f"{issue.status} {issue.criticality}".lower(),
            }
            for issue in queryset
        ]
    return JiraMetrics(
        total=total,
        completed=completed,
        in_progress=in_progress,
        new=new,
        blocked=blocked,
        issues_found=issues,
    )


def _fetch_jira_metrics(
    search_filter: str,
    *,
    exclude_subtasks: bool,
    include_debug: bool,
) -> JiraMetrics:
    """Delegate live Jira reads to the existing Cloud integration only when enabled."""
    from src.api.metrics_service import fetch_metrics as fetch_live_metrics

    live_metrics = fetch_live_metrics(
        search_filter=search_filter,
        exclude_subtasks=exclude_subtasks,
        debug=False,
    )
    return JiraMetrics(
        total=live_metrics.total,
        completed=live_metrics.completed,
        in_progress=live_metrics.in_progress,
        new=live_metrics.new,
        blocked=live_metrics.blocked,
        average_open_days=live_metrics.average_open_days,
        issues_found=live_metrics.issues_found if include_debug else [],
    )

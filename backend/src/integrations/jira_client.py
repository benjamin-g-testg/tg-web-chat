"""Read and summarize Jira Cloud or the normalized local issue table."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests
from django.conf import settings
from django.db.models import Q

from src.database.models import JiraIssue

@dataclass(frozen=True)
class JiraMetrics:
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    new: int = 0
    blocked: int = 0
    average_open_days: int = 0
    issues_found: Optional[list[dict[str, object]]] = None
    status_distribution: Optional[dict[str, int]] = None

    def to_dict(self, include_debug: bool = False) -> dict[str, object]:
        result = {
            "total": self.total,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "new": self.new,
            "blocked": self.blocked,
            "average_open_days": self.average_open_days,
            "status_distribution": self.status_distribution or {},
        }
        if include_debug:
            result["debug_issues"] = self.issues_found or []
        return result


def fetch_metrics(
    search_filter: str = "",
    *,
    exclude_subtasks: bool = True,
    include_debug: bool = False,
    filters: Optional[dict[str, object]] = None,
) -> JiraMetrics:
    """Summarize the configured source without making an implicit network call."""
    if getattr(settings, "JIRA_DATA_SOURCE", "local").lower() == "jira":
        return _fetch_jira_metrics(
            search_filter,
            exclude_subtasks=exclude_subtasks,
            include_debug=include_debug,
            filters=filters or {},
        )
    return _fetch_local_metrics(
        search_filter,
        exclude_subtasks=exclude_subtasks,
        include_debug=include_debug,
        filters=filters or {},
    )


def _fetch_local_metrics(
    search_filter: str,
    *,
    exclude_subtasks: bool,
    include_debug: bool,
    filters: dict[str, object],
) -> JiraMetrics:
    """Read the normalized JiraIssue table populated by the Excel importer."""
    queryset = JiraIssue.objects.all()
    if exclude_subtasks:
        queryset = queryset.exclude(issue_type__iregex=r"^Sub[- ]?task$")
    if search_filter:
        queryset = queryset.filter(
            Q(issue_key__icontains=search_filter)
            | Q(status__icontains=search_filter)
            | Q(criticality__icontains=search_filter)
            | Q(phase__icontains=search_filter)
            | Q(assignee__icontains=search_filter)
        )
    if filters.get("issue_key"):
        queryset = queryset.filter(issue_key__iexact=str(filters["issue_key"]))
    if filters.get("assignee"):
        queryset = queryset.filter(assignee__icontains=str(filters["assignee"]))
    if filters.get("assignee_me"):
        current_user = getattr(settings, "JIRA_CURRENT_USER", "") or getattr(settings, "JIRA_USER", "")
        queryset = queryset.filter(assignee__icontains=current_user) if current_user else queryset.none()
    if filters.get("status_category"):
        category = str(filters["status_category"])
        if category == "blocked":
            queryset = queryset.filter(Q(status__icontains="bloque") | Q(criticality__icontains="bloque"))
        else:
            queryset = queryset.filter(status_category__iexact=category)
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
    status_distribution: dict[str, int] = {}
    for issue in queryset:
        status_distribution[issue.status or "Sin estado"] = status_distribution.get(issue.status or "Sin estado", 0) + 1
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
                "assignee": issue.assignee,
                "criticality": issue.criticality,
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
        status_distribution=status_distribution,
    )


def _fetch_jira_metrics(
    search_filter: str,
    *,
    exclude_subtasks: bool,
    include_debug: bool,
    filters: dict[str, object],
) -> JiraMetrics:
    """Fetch all matching issues through Jira Cloud's paginated REST API."""
    issues = _fetch_jira_issues(search_filter, exclude_subtasks=exclude_subtasks, filters=filters)
    if filters.get("limit"):
        issues = issues[:int(filters["limit"])]
    total = len(issues)
    completed = sum(_status_category(issue) == "done" for issue in issues)
    in_progress = sum(_status_category(issue) == "indeterminate" for issue in issues)
    new = sum(_status_category(issue) == "new" for issue in issues)
    blocked = sum(_is_blocked(issue) for issue in issues)
    status_distribution: dict[str, int] = {}
    for issue in issues:
        fields = issue.get("fields", {})
        status = fields.get("status", {}) if isinstance(fields, dict) else {}
        status_name = status.get("name", "Sin estado") if isinstance(status, dict) else "Sin estado"
        status_distribution[str(status_name)] = status_distribution.get(str(status_name), 0) + 1
    issues_debug = [_issue_debug_data(issue) for issue in issues] if include_debug else []
    return JiraMetrics(
        total=total,
        completed=completed,
        in_progress=in_progress,
        new=new,
        blocked=blocked,
        average_open_days=_average_open_days(issues),
        issues_found=issues_debug,
        status_distribution=status_distribution,
    )


def _fetch_jira_issues(search_filter: str, *, exclude_subtasks: bool, filters: dict[str, object]) -> list[dict[str, object]]:
    server = (getattr(settings, "JIRA_SERVER", "") or "").rstrip("/")
    user = getattr(settings, "JIRA_USER", "") or ""
    token = getattr(settings, "JIRA_API_TOKEN", "") or ""
    if not server or not user or not token:
        raise RuntimeError("Faltan JIRA_SERVER, JIRA_USER o JIRA_API_TOKEN.")

    clauses = ['project = "TATC"']
    if exclude_subtasks:
        clauses.append('issuetype not in ("Sub-task", "Subtask")')
    if search_filter:
        safe_filter = search_filter.replace("\\", "\\\\").replace('"', '\\"')
        clauses.append(f'(summary ~ "{safe_filter}" OR status ~ "{safe_filter}")')
    if filters.get("issue_key"):
        clauses.append(f'key = "{_escape_jql(str(filters["issue_key"]))}"')
    if filters.get("assignee"):
        clauses.append(f'assignee ~ "{_escape_jql(str(filters["assignee"]))}"')
    if filters.get("assignee_me"):
        clauses.append("assignee = currentUser()")
    if filters.get("status_category") == "done":
        clauses.append('statusCategory = Done')
    elif filters.get("status_category") == "indeterminate":
        clauses.append('statusCategory = "In Progress"')
    elif filters.get("status_category") == "new":
        clauses.append('statusCategory = New')
    elif filters.get("status_category") == "blocked":
        clauses.append('(status ~ "bloque" OR priority ~ "bloqueante" OR status ~ "blocked")')
    jql = " AND ".join(clauses) + " ORDER BY created ASC"
    auth = (user, token)
    headers = {"Accept": "application/json"}
    issues: list[dict[str, object]] = []
    next_page_token: Optional[str] = None

    while True:
        payload: dict[str, object] = {
            "jql": jql,
            "maxResults": 100,
            "fields": [
                "summary", "status", "issuetype", "priority", "created", "updated",
                "assignee", "reporter", "resolutiondate",
            ],
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        response = requests.post(
            f"{server}/rest/api/3/search/jql",
            auth=auth,
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Jira respondió HTTP {response.status_code}: {response.text[:300]}")
        page = response.json()
        page_issues = page.get("issues", [])
        issues.extend(page_issues)
        next_page_token = page.get("nextPageToken")
        if not next_page_token or not page_issues:
            return issues


def _status_category(issue: dict[str, object]) -> str:
    fields = issue.get("fields", {})
    status = fields.get("status", {}) if isinstance(fields, dict) else {}
    category = status.get("statusCategory", {}) if isinstance(status, dict) else {}
    return str(category.get("key", "")).lower() if isinstance(category, dict) else ""


def _escape_jql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _is_blocked(issue: dict[str, object]) -> bool:
    fields = issue.get("fields", {})
    if not isinstance(fields, dict):
        return False
    status = fields.get("status", {})
    priority = fields.get("priority", {})
    status_name = status.get("name", "") if isinstance(status, dict) else ""
    priority_name = priority.get("name", "") if isinstance(priority, dict) else ""
    text = f"{status_name} {priority_name}".lower()
    return "bloque" in text or "blocked" in text


def _average_open_days(issues: list[dict[str, object]]) -> int:
    now = datetime.now(timezone.utc)
    ages = []
    for issue in issues:
        fields = issue.get("fields", {})
        if not isinstance(fields, dict) or _status_category(issue) == "done":
            continue
        created = fields.get("created")
        if not created:
            continue
        try:
            created_at = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        except ValueError:
            continue
        ages.append(max((now - created_at).days, 0))
    return round(sum(ages) / len(ages)) if ages else 0


def _issue_debug_data(issue: dict[str, object]) -> dict[str, object]:
    fields = issue.get("fields", {})
    if not isinstance(fields, dict):
        fields = {}
    status = fields.get("status", {})
    priority = fields.get("priority", {})
    issue_type = fields.get("issuetype", {})
    assignee = fields.get("assignee", {})
    return {
        "key": issue.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": status.get("name", "") if isinstance(status, dict) else "",
        "category": _status_category(issue),
        "priority": priority.get("name", "") if isinstance(priority, dict) else "",
        "type": issue_type.get("name", "") if isinstance(issue_type, dict) else "",
        "assignee": assignee.get("displayName", "") if isinstance(assignee, dict) else "",
        "blocked": _is_blocked(issue),
    }

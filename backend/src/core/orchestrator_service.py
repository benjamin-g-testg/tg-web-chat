"""Cost-aware orchestration boundary for local and GitHub-backed executions."""
from django.conf import settings

from src.database.models import AnalysisJob, Session
from src.integrations.github_actions_client import dispatch_workflow


def create_analysis_job(session: Session, request_text: str, intent: str) -> AnalysisJob:
    """Create a job and execute the local provider until GitHub is configured."""
    mode = getattr(settings, "AGENT_EXECUTION_MODE", "mock")
    agent = _select_agent(intent)
    job = AnalysisJob.objects.create(
        session=session,
        request_text=request_text,
        status=AnalysisJob.Status.PLANNING,
        progress=20,
        stage="planning",
        selected_agent=agent,
        execution_mode=mode,
    )

    if mode == "github_actions" and agent != "python":
        try:
            dispatch_workflow(
                f"ejecutar_consulta_jira_{agent}",
                {
                    "request_id": str(job.id),
                    "user_query": request_text,
                    "jira_base_url": getattr(settings, "JIRA_SERVER", ""),
                    "jira_email": getattr(settings, "JIRA_USER", ""),
                    "ref": getattr(settings, "GITHUB_WORKFLOW_BRANCH", "test"),
                },
            )
            job.status = AnalysisJob.Status.RUNNING
            job.progress = 30
            job.stage = "dispatched"
            job.save(update_fields=["status", "progress", "stage", "updated_at"])
        except Exception as error:
            job.status = AnalysisJob.Status.FAILED
            job.stage = "dispatch_failed"
            job.error = str(error)
            job.save(update_fields=["status", "stage", "error", "updated_at"])
    elif mode == "mock":
        job.status = AnalysisJob.Status.COMPLETED
        job.progress = 100
        job.stage = "completed"
        job.result = {
            "provider": "python-mock",
            "intent": intent,
            "agent": agent,
            "message": "Job preparado para conectarse con GitHub Actions.",
        }
        job.save(update_fields=["status", "progress", "stage", "result", "updated_at"])
    return job


def _select_agent(intent: str) -> str:
    if intent in {"create_report", "general_query"}:
        return "codex"
    if intent in {"list_blocked", "list_by_status", "filter_issues"}:
        return "python"
    return "python"


def serialize_job(job: AnalysisJob) -> dict[str, object]:
    return {
        "id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "stage": job.stage,
        "agent": job.selected_agent,
        "execution_mode": job.execution_mode,
        "result": job.result,
        "error": job.error or None,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
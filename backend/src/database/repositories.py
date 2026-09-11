"""Repository functions isolate ORM operations from the HTTP layer."""
from uuid import UUID
from .models import AnalysisExecution, ChatMessage, Session


def get_or_create_session(session_id: str | None, title: str, search_filter: str, analysis: str) -> Session:
    if session_id:
        try:
            session = Session.objects.get(id=UUID(session_id))
            session.search_filter, session.analysis_requested = search_filter, analysis
            session.save(update_fields=["search_filter", "analysis_requested", "updated_at"])
            return session
        except (Session.DoesNotExist, ValueError):
            pass
    return Session.objects.create(title=title, search_filter=search_filter, analysis_requested=analysis)


def save_execution(session: Session, reports: dict[str, str], metrics: dict[str, int | float]) -> AnalysisExecution:
    return AnalysisExecution.objects.create(session=session, report_fase_1=reports["phase_1"], report_fase_2=reports["phase_2"], report_fase_3=reports["phase_3"], report_conclusion=reports["conclusion"], report_resumen_ejecutivo=reports["executive_summary"], total_issues=int(metrics["total_issues"]), blocked_issues=int(metrics["blocked_issues"]), completion_rate=metrics["completion_rate"])

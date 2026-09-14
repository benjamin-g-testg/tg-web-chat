"""HTTP endpoints validate payloads and delegate all business work to services."""
from pathlib import Path
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse
from django.utils.html import escape
from django.conf import settings

from src.core.services import run_qa_pipeline
from src.database.models import AnalysisJob, Session, ChatMessage
from src.database.repositories import get_or_create_session, save_execution
from src.core.orchestrator_service import (
    create_analysis_job,
    complete_local_job,
    fail_local_job,
    serialize_job,
)
from src.integrations.jira_client import fetch_metrics
from src.agents.agent_service import JiraAgent
from src.agents.local_agent_service import run_local_agent_analysis
from src.core.report_service import generate_reports


class ChatView(APIView):
    """
    Endpoint POST /api/chat/
    Procesa consultas en lenguaje natural, detecta intenciones, ejecuta
    el pipeline de QA sobre Jira y genera reportes descargables en DOCX y PDF.
    """

    def post(self, request: object) -> Response:
        data = request.data
        raw_message = str(data.get("message", "")).strip()
        message = raw_message

        # Validación: mensaje obligatorio y longitud máxima
        if not message:
            return Response(
                {"detail": "El mensaje es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(message) > settings.MAX_MESSAGE_LENGTH:
            return Response(
                {"detail": f"Mensaje excede el máximo permitido ({settings.MAX_MESSAGE_LENGTH} caracteres)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sanitización contra inyecciones XSS
        message = escape(message)

        search_filter = str(data.get("search_filter", "")).strip()
        if len(search_filter) > settings.MAX_FILTER_LENGTH:
            search_filter = search_filter[:settings.MAX_FILTER_LENGTH]

        analysis = str(data.get("analysis_requested", "")).strip()

        # Obtener o crear sesión
        session = get_or_create_session(
            data.get("session_id"),
            message[:80],
            search_filter,
            analysis,
        )

        # Guardar mensaje del usuario
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=message,
        )

        # Procesar con JiraAgent para detección inteligente de intenciones
        agent = JiraAgent()
        agent_response = agent.process_message(raw_message)
        filters = agent_response.data.get("filters", {}) if agent_response.data else {}
        if not isinstance(filters, dict):
            filters = {}
        if agent_response.data and agent_response.data.get("limit"):
            filters["limit"] = agent_response.data["limit"]
        if not search_filter and agent_response.data:
            extracted_filter = agent_response.data.get("filter")
            if isinstance(extracted_filter, str):
                search_filter = extracted_filter.strip()

        job = create_analysis_job(session, message, agent_response.intent.value)
        output_dir = Path(settings.BASE_DIR).parent / "04_Resultado_del_Analisis" / str(job.id)

        # Ejecutar pipeline QA
        try:
            result = run_qa_pipeline(message, search_filter, analysis, filters=filters)
            if job.execution_mode == "local" and getattr(settings, "AGENT_PROVIDER", "codex") in ("codex", "agy", "antigravity"):
                result["agent_context"]["intent"] = agent_response.intent.value
                result["agent_context"]["action"] = agent_response.action
                result["agent_context"]["request_data"] = agent_response.data or {}
                try:
                    agent_reports = run_local_agent_analysis(message, result["agent_context"], output_dir)
                    result["chat_response"] = agent_reports.pop("chat_response", "")
                    result["reports"].update({k: v for k, v in agent_reports.items() if v})
                    result["agent"] = {"provider": getattr(settings, "AGENT_PROVIDER", "codex"), "reports": agent_reports}
                except Exception as agent_error:
                    result["agent"] = {"provider": getattr(settings, "AGENT_PROVIDER", "codex"), "warning": str(agent_error)}

            # Siempre generar los artefactos descargables Word (.docx) y PDF (.pdf)
            result["artifacts"] = generate_reports(output_dir, result["reports"], result["agent_context"])

        except Exception as error:
            if job.execution_mode == "local":
                fail_local_job(job, error)
            raise

        if job.execution_mode == "local":
            complete_local_job(job, result)

        # Guardar ejecución en base de datos
        execution = save_execution(session, result["reports"], result["metrics"])

        # Guardar respuesta del asistente
        assistant_content = result.get("chat_response") or result["reports"]["phase_3"]
        assistant = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_content,
        )

        return Response(
            {
                "session": {
                    "id": str(session.id),
                    "title": session.title,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                },
                "message": {
                    "id": str(assistant.id),
                    "content": assistant.content,
                    "timestamp": assistant.timestamp.isoformat(),
                },
                "reports": result["reports"],
                "metrics": result["metrics"],
                "execution_id": str(execution.id),
                "job": serialize_job(job),
                "agent": {
                    "intent": agent_response.intent.value,
                    "action": agent_response.action,
                    "message": agent_response.message,
                    "data": agent_response.data,
                },
                "artifacts": result.get("artifacts", {}),
            },
            status=status.HTTP_201_CREATED,
        )


class SessionListView(APIView):
    """
    GET /api/sessions/
    Retorna el listado de sesiones ordenadas cronológicamente con conteo de mensajes.
    """

    def get(self, request) -> Response:
        order = request.query_params.get("order", "desc").lower()
        order_field = "-updated_at" if order == "desc" else "updated_at"
        sessions = Session.objects.all().order_by(order_field)[:100]

        return Response([
            {
                "id": str(s.id),
                "title": s.title,
                "filter": s.search_filter,
                "analysis": s.analysis_requested,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "message_count": s.messages.count(),
            }
            for s in sessions
        ])


class SessionDetailView(APIView):
    """
    GET, PATCH, DELETE /api/sessions/<uuid:session_id>/
    - GET: Retorna mensajes, reportes y métricas de la sesión.
    - PATCH: Modifica el título de la sesión.
    - DELETE: Elimina la sesión y todos sus registros asociados.
    """

    def get(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response({"detail": "Sesión no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        messages = [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in session.messages.all()
        ]

        last_execution = session.executions.order_by("-created_at").first()
        last_job = session.jobs.order_by("-created_at").first()

        reports = None
        metrics = None
        if last_execution:
            reports = {
                "phase_1": last_execution.report_fase_1,
                "phase_2": last_execution.report_fase_2,
                "phase_3": last_execution.report_fase_3,
                "conclusion": last_execution.report_conclusion,
                "executive_summary": last_execution.report_resumen_ejecutivo,
            }
            metrics = {
                "total": last_execution.total_issues,
                "completed": round(last_execution.total_issues * float(last_execution.completion_rate) / 100),
                "blocked": last_execution.blocked_issues,
                "completion_rate": float(last_execution.completion_rate),
            }

        artifacts = None
        if last_job and isinstance(last_job.result, dict):
            artifacts = last_job.result.get("artifacts")

        return Response({
            "session": {
                "id": str(session.id),
                "title": session.title,
                "search_filter": session.search_filter,
                "analysis_requested": session.analysis_requested,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            },
            "messages": messages,
            "reports": reports,
            "metrics": metrics,
            "artifacts": artifacts,
            "job": serialize_job(last_job) if last_job else None,
        })

    def patch(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response({"detail": "Sesión no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        new_title = str(request.data.get("title", "")).strip()
        if not new_title:
            return Response({"detail": "El título no puede estar vacío."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_title) > 160:
            new_title = new_title[:160]

        session.title = escape(new_title)
        session.save(update_fields=["title", "updated_at"])

        return Response({
            "id": str(session.id),
            "title": session.title,
            "updated_at": session.updated_at.isoformat(),
        })

    def delete(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response({"detail": "Sesión no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        session.delete()
        return Response({"detail": "Sesión eliminada correctamente."}, status=status.HTTP_200_OK)


class GlobalArtifactsView(APIView):
    """
    GET /api/artifacts/
    Retorna el inventario consolidado de todos los archivos y reportes generados
    en el sistema agrupados por sesión y ordenados cronológicamente.
    """

    def get(self, request):
        jobs = AnalysisJob.objects.filter(status=AnalysisJob.Status.COMPLETED).select_related("session").order_by("-created_at")[:100]
        base_dir = Path(settings.BASE_DIR).parent / "04_Resultado_del_Analisis"
        inventory = []

        for job in jobs:
            artifacts_data = job.result.get("artifacts", {}) if isinstance(job.result, dict) else {}
            if not isinstance(artifacts_data, dict) or not artifacts_data:
                continue

            session = job.session
            job_dir = base_dir / str(job.id)
            file_items = []

            for format_type in ("word", "pdf"):
                format_files = artifacts_data.get(format_type, {})
                if isinstance(format_files, dict):
                    for phase_key, filename in format_files.items():
                        file_path = job_dir / filename
                        file_items.append({
                            "phase": phase_key,
                            "format": format_type,
                            "filename": filename,
                            "exists_on_disk": file_path.is_file(),
                            "size_bytes": file_path.stat().st_size if file_path.is_file() else 0,
                            "download_url": f"/api/jobs/{job.id}/artifacts/{format_type}/{filename}",
                        })

            if file_items:
                inventory.append({
                    "job_id": str(job.id),
                    "session_id": str(session.id),
                    "session_title": session.title,
                    "created_at": job.created_at.isoformat(),
                    "files": file_items,
                })

        return Response({"total_jobs": len(inventory), "inventory": inventory})


class AnalysisJobView(APIView):
    """
    GET /api/jobs/<uuid:job_id>/
    Retorna el estado de ejecución y progreso de un Job de análisis.
    """

    def get(self, _, job_id):
        try:
            job = AnalysisJob.objects.get(id=job_id)
        except AnalysisJob.DoesNotExist:
            return Response({"detail": "Job no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_job(job))


class ArtifactView(APIView):
    """
    GET /api/jobs/<uuid:job_id>/artifacts/<str:format_name>/<str:artifact_name>
    Descarga o visualiza artefactos generados (DOCX / PDF).
    """

    def get(self, request, job_id, format_name, artifact_name):
        try:
            job = AnalysisJob.objects.get(id=job_id)
        except AnalysisJob.DoesNotExist:
            return Response({"detail": "Job no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        artifacts = job.result.get("artifacts", {}) if isinstance(job.result, dict) else {}
        allowed = artifacts.get(format_name, {}) if isinstance(artifacts, dict) else {}
        filename = next((value for value in allowed.values() if value == artifact_name), None) if isinstance(allowed, dict) else None

        if not filename or Path(filename).name != filename:
            return Response({"detail": "Archivo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        path = Path(settings.BASE_DIR).parent / "04_Resultado_del_Analisis" / str(job.id) / filename
        if not path.is_file():
            return Response({"detail": "Archivo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(path.open("rb"), as_attachment=format_name != "pdf", filename=filename)


class MetricsView(APIView):
    """
    GET /api/metrics/
    Devuelve métricas de incidencias del proyecto TATC clasificadas por categoría global.
    """

    def get(self, request):
        exclude_subtasks = request.query_params.get("exclude_subtasks", "true").lower() == "true"
        debug = request.query_params.get("debug", "false").lower() == "true"

        metrics = fetch_metrics(
            exclude_subtasks=exclude_subtasks,
            include_debug=debug,
        )
        return Response(metrics.to_dict(include_debug=debug))
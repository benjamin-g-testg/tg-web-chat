"""HTTP endpoints validate payloads and delegate all business work to services."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.html import escape
from django.conf import settings
from src.core.services import run_qa_pipeline
from src.database.models import AnalysisJob, Session
from src.database.repositories import get_or_create_session, save_execution
from src.database.models import ChatMessage
from src.core.orchestrator_service import create_analysis_job, serialize_job
from src.integrations.jira_client import fetch_metrics
from src.agents.agent_service import JiraAgent
# from .metrics_service_bd_local import fetch_metrics_bd as fetch_metrics / Para probar con datos historicos

class ChatView(APIView):
    def post(self, request: object) -> Response:
        data = request.data
        message = str(data.get("message", "")).strip()
        
        # Phase 1: Validación - mensaje vacío o muy largo
        if not message:
            return Response(
                {"detail": "El mensaje es obligatorio."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(message) > settings.MAX_MESSAGE_LENGTH:
            return Response(
                {"detail": f"Mensaje muy largo (máx {settings.MAX_MESSAGE_LENGTH} caracteres)"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Phase 1: Sanitizar mensaje (prevenir XSS)
        message = escape(message)
        
        search_filter = str(data.get("search_filter", "")).strip()
        if len(search_filter) > settings.MAX_FILTER_LENGTH:
            search_filter = search_filter[:settings.MAX_FILTER_LENGTH]
        
        analysis = str(data.get("analysis_requested", "")).strip()
        
        # Crear/obtener sesión
        session = get_or_create_session(
            data.get("session_id"), 
            message[:80], 
            search_filter, 
            analysis
        )
        
        # Guardar mensaje del usuario
        ChatMessage.objects.create(
            session=session, 
            role=ChatMessage.Role.USER, 
            content=message
        )
        
        # Phase 2: Procesar con JiraAgent
        agent = JiraAgent()
        agent_response = agent.process_message(message)
        job = create_analysis_job(session, message, agent_response.intent.value)
        
        # Ejecutar pipeline QA
        result = run_qa_pipeline(message, search_filter, analysis)
        
        # Guardar ejecución
        execution = save_execution(session, result["reports"], result["metrics"])
        
        # Guardar respuesta del asistente
        assistant = ChatMessage.objects.create(
            session=session, 
            role=ChatMessage.Role.ASSISTANT, 
            content=result["reports"]["conclusion"]
        )
        
        return Response(
            {
                "session": {"id": str(session.id), "title": session.title}, 
                "message": {
                    "id": str(assistant.id), 
                    "content": assistant.content, 
                    "timestamp": assistant.timestamp
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
                }
            }, 
            status=status.HTTP_201_CREATED
        )


class AnalysisJobView(APIView):
    def get(self, _, job_id):
        try:
            job = AnalysisJob.objects.get(id=job_id)
        except AnalysisJob.DoesNotExist:
            return Response({"detail": "Job no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_job(job))


class SessionListView(APIView):
    def get(self, _: object) -> Response:
        sessions = Session.objects.all()[:30]
        return Response([{"id": str(s.id), "title": s.title, "filter": s.search_filter, "analysis": s.analysis_requested, "updated_at": s.updated_at} for s in sessions])


class MetricsView(APIView):
    """
    GET /api/metrics/
    Devuelve métricas de incidencias del proyecto TATC clasificadas por categoría global.
    
    Query params:
    - exclude_subtasks (bool, default=True): Excluir subtareas
    - debug (bool, default=False): Incluir lista detallada de incidencias
    """
    def get(self, request):
        exclude_subtasks = request.query_params.get('exclude_subtasks', 'true').lower() == 'true'
        debug = request.query_params.get('debug', 'false').lower() == 'true'
        
        metrics = fetch_metrics(
            exclude_subtasks=exclude_subtasks,
            include_debug=debug,
        )
        return Response(metrics.to_dict(include_debug=debug))
"""HTTP endpoints validate payloads and delegate all business work to services."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from src.core.services import run_qa_pipeline
from src.database.models import Session
from src.database.repositories import get_or_create_session, save_execution
from src.database.models import ChatMessage


class ChatView(APIView):
    def post(self, request: object) -> Response:
        data = request.data
        message = str(data.get("message", "")).strip()
        if not message:
            return Response({"detail": "El mensaje es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        search_filter, analysis = str(data.get("search_filter", "")), str(data.get("analysis_requested", ""))
        session = get_or_create_session(data.get("session_id"), message[:80], search_filter, analysis)
        ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content=message)
        result = run_qa_pipeline(message, search_filter, analysis)
        execution = save_execution(session, result["reports"], result["metrics"])
        assistant = ChatMessage.objects.create(session=session, role=ChatMessage.Role.ASSISTANT, content=result["reports"]["conclusion"])
        return Response({"session": {"id": str(session.id), "title": session.title}, "message": {"id": str(assistant.id), "content": assistant.content, "timestamp": assistant.timestamp}, "reports": result["reports"], "metrics": result["metrics"], "execution_id": str(execution.id)}, status=status.HTTP_201_CREATED)


class SessionListView(APIView):
    def get(self, _: object) -> Response:
        sessions = Session.objects.all()[:30]
        return Response([{"id": str(s.id), "title": s.title, "filter": s.search_filter, "analysis": s.analysis_requested, "updated_at": s.updated_at} for s in sessions])

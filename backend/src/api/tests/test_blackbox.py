"""
Pruebas de Caja Negra (Black-box testing).
Evalua el comportamiento externo de los endpoints de la API REST,
codigos de respuesta HTTP, validaciones de seguridad, sanitizacion XSS
y casos borde de entrada.
"""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
import uuid

from src.database.models import Session, ChatMessage, JiraIssue, AnalysisJob


@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class ChatEndpointBlackBoxTests(TestCase):
    """Pruebas de caja negra sobre POST /api/chat/"""

    def setUp(self):
        self.client = APIClient()
        JiraIssue.objects.create(
            jira_id="2001",
            issue_key="TATC-10",
            status="Finalizado",
            status_category="done",
            criticality="Baja",
            assignee="Carlos Silva",
            issue_type="Task",
            description="Configuracion de pipeline",
        )

    def test_post_chat_valid_message(self):
        payload = {
            "message": "Realizar analisis de calidad del proyecto",
            "search_filter": "",
            "analysis_requested": "Evaluar riesgos",
        }
        response = self.client.post("/api/chat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("session", response.data)
        self.assertIn("message", response.data)
        self.assertIn("reports", response.data)
        self.assertIn("metrics", response.data)
        self.assertIn("agent", response.data)

        session_id = response.data["session"]["id"]
        self.assertTrue(Session.objects.filter(id=session_id).exists())

    def test_post_chat_empty_message_rejected(self):
        payload = {"message": "   ", "search_filter": "", "analysis_requested": ""}
        response = self.client.post("/api/chat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_post_chat_oversized_message_rejected(self):
        payload = {"message": "A" * 5001, "search_filter": "", "analysis_requested": ""}
        response = self.client.post("/api/chat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_chat_xss_sanitization(self):
        malicious_input = '<script>alert("XSS")</script>Analisis'
        payload = {"message": malicious_input, "search_filter": "", "analysis_requested": ""}
        response = self.client.post("/api/chat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        session_id = response.data["session"]["id"]
        user_message = ChatMessage.objects.filter(
            session_id=session_id,
            role=ChatMessage.Role.USER,
        ).first()
        self.assertIsNotNone(user_message)
        self.assertNotIn("<script>", user_message.content)
        self.assertIn("&lt;script&gt;", user_message.content)


@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class SessionsEndpointBlackBoxTests(TestCase):
    """Pruebas de caja negra para los endpoints de sesiones."""

    def setUp(self):
        self.client = APIClient()
        self.session = Session.objects.create(
            title="Sesion de prueba",
            search_filter="Filtro A",
            analysis_requested="Analisis B",
        )
        ChatMessage.objects.create(
            session=self.session,
            role=ChatMessage.Role.USER,
            content="Hola asistente",
        )
        ChatMessage.objects.create(
            session=self.session,
            role=ChatMessage.Role.ASSISTANT,
            content="Respuesta del asistente",
        )

    def test_get_session_list(self):
        response = self.client.get("/api/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.session.id))

    def test_get_session_detail_existing(self):
        response = self.client.get(f"/api/sessions/{self.session.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session"]["id"], str(self.session.id))
        self.assertEqual(len(response.data["messages"]), 2)

    def test_get_session_detail_not_found(self):
        random_uuid = uuid.uuid4()
        response = self.client.get(f"/api/sessions/{random_uuid}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class MetricsAndJobsEndpointBlackBoxTests(TestCase):
    """Pruebas de caja negra para metricas y jobs."""

    def setUp(self):
        self.client = APIClient()
        self.session = Session.objects.create(title="Sesion Job")
        self.job = AnalysisJob.objects.create(
            session=self.session,
            request_text="Consulta de prueba",
            status=AnalysisJob.Status.COMPLETED,
            progress=100,
            stage="completed",
        )

    def test_get_metrics_endpoint(self):
        response = self.client.get("/api/metrics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)
        self.assertIn("completed", response.data)
        self.assertIn("blocked", response.data)

    def test_get_job_detail_existing(self):
        response = self.client.get(f"/api/jobs/{self.job.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.job.id))
        self.assertEqual(response.data["status"], "completed")

    def test_get_job_detail_not_found(self):
        random_uuid = uuid.uuid4()
        response = self.client.get(f"/api/jobs/{random_uuid}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

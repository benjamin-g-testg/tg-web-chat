"""
Consultas en lenguaje natural contra POST /api/chat/.
Comprueba intenciones, filtros y que las respuestas usen los datos de Jira.
"""
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from src.agents.agent_service import IntentType, JiraAgent
from src.database.models import JiraIssue


@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock", AGENT_EXECUTION_MODE="local")
class NaturalLanguageChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.agent = JiraAgent()
        JiraIssue.objects.create(
            jira_id="nl-1",
            issue_key="TATC-10",
            status="Termino Exitoso",
            status_category="done",
            criticality="Baja",
            assignee="Carlos Silva",
            issue_type="Task",
            description="Cierre del pipeline de certificacion",
        )
        JiraIssue.objects.create(
            jira_id="nl-2",
            issue_key="TATC-20",
            status="En curso",
            status_category="indeterminate",
            criticality="Alta",
            assignee="Ana Perez",
            issue_type="Bug",
            description="Ajuste de login en ambiente QA",
        )
        JiraIssue.objects.create(
            jira_id="nl-3",
            issue_key="TATC-30",
            status="Bloqueado",
            status_category="indeterminate",
            criticality="Bloqueante",
            assignee="Luis Soto",
            issue_type="Task",
            description="Espera de credenciales del proveedor",
        )
        JiraIssue.objects.create(
            jira_id="nl-4",
            issue_key="TATC-40",
            status="Backlog",
            status_category="new",
            criticality="Media",
            assignee="",
            issue_type="Story",
            description="Definir casos de prueba de regresion",
        )

    def _ask(self, message: str):
        response = self.client.post("/api/chat/", {"message": message}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        body = response.json() if hasattr(response, "json") else response.data
        serialized = str(body)
        self.assertNotIn("JIRA_API_TOKEN", serialized)
        self.assertNotIn("OPENAI_API_KEY", serialized)
        self.assertNotIn("GEMINI_API_KEY", serialized)
        return body

    def test_inventory_question(self):
        body = self._ask("cuantas incidencias hay en el proyecto TATC?")
        self.assertGreaterEqual(body["metrics"]["total"], 4)
        self.assertIn("TATC", body["message"]["content"])

    def test_blocked_question(self):
        intent = self.agent.detect_intent("cuales estan bloqueados ahora mismo?")
        self.assertEqual(intent, IntentType.LIST_BLOCKED)
        body = self._ask("cuales estan bloqueados ahora mismo?")
        content = body["message"]["content"].lower()
        self.assertIn("tatc-30", content)
        self.assertIn("bloquead", content)

    def test_in_progress_question(self):
        body = self._ask("mostrame los tickets que estan en curso")
        content = body["message"]["content"].lower()
        self.assertIn("tatc-20", content)
        self.assertIn("ana perez", content)

    def test_backlog_question(self):
        body = self._ask("que hay pendiente en el backlog?")
        content = body["message"]["content"].lower()
        self.assertIn("tatc-40", content)

    def test_completed_owners_question(self):
        body = self._ask("quien esta a cargo de los issues completados?")
        content = body["message"]["content"].lower()
        self.assertIn("carlos silva", content)
        self.assertIn("tatc-10", content)

    def test_specific_issue_by_key(self):
        body = self._ask("dame la informacion del issue TATC-10")
        content = body["message"]["content"]
        self.assertIn("TATC-10", content)
        self.assertIn("Carlos Silva", content)

    def test_specific_issue_by_number(self):
        parsed = self.agent.process_message("analiza el ticket 20")
        self.assertEqual(parsed.data["filters"]["issue_key"], "TATC-20")
        body = self._ask("analiza el ticket 20")
        self.assertIn("TATC-20", body["message"]["content"])

    def test_metrics_endpoint_does_not_expose_secrets(self):
        response = self.client.get("/api/metrics/?debug=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serialized = str(response.data)
        self.assertNotIn("JIRA_API_TOKEN", serialized)
        self.assertIn("total", response.data)

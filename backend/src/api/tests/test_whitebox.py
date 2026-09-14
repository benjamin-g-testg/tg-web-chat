"""
Pruebas de Caja Blanca (White-box testing).
Verifica normalización con caracteres internacionales/emojis, intenciones,
métricas Jira, cálculo de días, serialización y resiliencia ante nulos.
"""
from django.test import TestCase, override_settings
from src.agents.agent_service import (
    JiraAgent,
    IntentType,
    normalize_text,
    extract_status,
)
from src.integrations.jira_client import (
    _status_category,
    _is_blocked,
    _issue_debug_data,
    _average_open_days,
    _escape_jql,
)
from src.core.services import run_qa_pipeline
from src.core.report_service import _paragraphs, _escape_pdf_text
from src.database.models import Session, JiraIssue
from src.database.repositories import get_or_create_session, save_execution


class TextNormalizationTests(TestCase):
    """Pruebas unitarias para el normalizador de texto y resiliencia ante caracteres especiales."""

    def test_accents_and_case(self):
        text = "¡INFORMACIÓN DE ANÁLISIS y Riesgós!"
        normalized = normalize_text(text)
        self.assertEqual(normalized, "informacion de analisis y riesgos")

    def test_special_characters_and_spaces(self):
        text = "   Ticket   #8:   Error en login... (CRÍTICO)   "
        normalized = normalize_text(text)
        self.assertEqual(normalized, "ticket #8 error en login critico")

    def test_international_characters_and_emojis(self):
        # Texto con cirílico, kanji y caracteres extraños
        text = "Incidencia QA 🚀 Привет 世界 #99"
        normalized = normalize_text(text)
        self.assertIn("incidencia qa", normalized)
        self.assertIn("#99", normalized)

    def test_empty_string(self):
        self.assertEqual(normalize_text(""), "")


class StatusExtractionTests(TestCase):
    """Pruebas unitarias para la deducción de estados y categorías."""

    def test_exact_and_alias_matches(self):
        self.assertEqual(extract_status("completados"), "done")
        self.assertEqual(extract_status("terminado"), "done")
        self.assertEqual(extract_status("en curso"), "indeterminate")
        self.assertEqual(extract_status("in progress"), "indeterminate")
        self.assertEqual(extract_status("por hacer"), "new")
        self.assertEqual(extract_status("bloqueado"), "blocked")

    def test_fuzzy_status_matches(self):
        # Errores tipográficos comunes
        self.assertEqual(extract_status("completadass"), "done")
        self.assertEqual(extract_status("bloqeados"), "blocked")

    def test_unknown_status(self):
        self.assertEqual(extract_status("xyz123 aleatorio"), "")


class JiraAgentLogicTests(TestCase):
    """Pruebas de caja blanca para JiraAgent."""

    def setUp(self):
        self.agent = JiraAgent()

    def test_detect_intent_blocked(self):
        intent = self.agent.detect_intent("cuales son los issues bloqueados")
        self.assertEqual(intent, IntentType.LIST_BLOCKED)

    def test_detect_intent_by_status(self):
        intent = self.agent.detect_intent("muestrame los tickets en curso")
        self.assertEqual(intent, IntentType.LIST_BY_STATUS)

    def test_detect_intent_report(self):
        intent = self.agent.detect_intent("dame un reporte con estadisticas generales")
        self.assertEqual(intent, IntentType.CREATE_REPORT)

    def test_detect_intent_export_excel(self):
        intent = self.agent.detect_intent("quiero descargar el excel de resultados")
        self.assertEqual(intent, IntentType.EXPORT_EXCEL)

    def test_detect_intent_filter(self):
        intent = self.agent.detect_intent('filtrar por "Sprint 3"')
        self.assertEqual(intent, IntentType.FILTER_ISSUES)

    def test_process_message_with_assignee_and_key(self):
        response = self.agent.process_message("Revisa el issue TATC-12 asignado a Benjamin Garaya")
        self.assertIsNotNone(response.data)
        filters = response.data.get("filters", {})
        self.assertEqual(filters.get("issue_key"), "TATC-12")
        self.assertIn("benjamin garaya", filters.get("assignee", "").lower())

    def test_process_message_with_assignee_me(self):
        response = self.agent.process_message("cuales son mis tickets asignados a mi?")
        filters = response.data.get("filters", {})
        self.assertTrue(filters.get("assignee_me"))

    def test_process_message_with_numeric_ticket(self):
        response = self.agent.process_message("analizar el ticket 45")
        filters = response.data.get("filters", {})
        self.assertEqual(filters.get("issue_key"), "TATC-45")


class JiraClientHelperTests(TestCase):
    """Pruebas unitarias para funciones auxiliares de Jira y resiliencia ante nulos."""

    def test_status_category_extraction(self):
        issue_done = {"fields": {"status": {"statusCategory": {"key": "done"}}}}
        issue_indeterminate = {"fields": {"status": {"statusCategory": {"key": "indeterminate"}}}}
        issue_empty = {}

        self.assertEqual(_status_category(issue_done), "done")
        self.assertEqual(_status_category(issue_indeterminate), "indeterminate")
        self.assertEqual(_status_category(issue_empty), "")

    def test_is_blocked_detection(self):
        issue_blocked_status = {"fields": {"status": {"name": "Bloqueado"}, "priority": {"name": "Media"}}}
        issue_blocked_priority = {"fields": {"status": {"name": "En curso"}, "priority": {"name": "Bloqueante"}}}
        issue_normal = {"fields": {"status": {"name": "Abierto"}, "priority": {"name": "Alta"}}}
        issue_null = {"fields": None}

        self.assertTrue(_is_blocked(issue_blocked_status))
        self.assertTrue(_is_blocked(issue_blocked_priority))
        self.assertFalse(_is_blocked(issue_normal))
        self.assertFalse(_is_blocked(issue_null))

    def test_average_open_days_calculation(self):
        issues_empty = []
        self.assertEqual(_average_open_days(issues_empty), 0)

        issues_done = [{"fields": {"created": "2026-01-01T00:00:00Z", "status": {"statusCategory": {"key": "done"}}}}]
        self.assertEqual(_average_open_days(issues_done), 0)

    def test_escape_jql(self):
        self.assertEqual(_escape_jql('Sprint "1" \\ Test'), 'Sprint \\"1\\" \\\\ Test')


class ReportHelperTests(TestCase):
    """Pruebas de utilidades de reportes."""

    def test_paragraphs_split(self):
        text = "Párrafo 1\n\nPárrafo 2\n\n\nPárrafo 3"
        parts = _paragraphs(text)
        self.assertEqual(len(parts), 3)

    def test_escape_pdf_text(self):
        self.assertEqual(_escape_pdf_text("Test <tag> & symbols"), "Test &lt;tag&gt; &amp; symbols")


@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class RepositoryAndPipelineTests(TestCase):
    """Pruebas de la capa de persistencia y pipeline QA determinista con BD local."""

    def setUp(self):
        JiraIssue.objects.create(
            jira_id="1001",
            issue_key="TATC-1",
            status="Finalizado",
            status_category="done",
            criticality="Media",
            assignee="Juan Perez",
            issue_type="Story",
            description="Historia de usuario inicial",
        )
        JiraIssue.objects.create(
            jira_id="1002",
            issue_key="TATC-2",
            status="Bloqueado",
            status_category="indeterminate",
            criticality="Bloqueante",
            assignee="Maria Gomez",
            issue_type="Bug",
            description="Defecto critico bloqueante",
        )

    def test_get_or_create_session(self):
        session = get_or_create_session(None, "Nueva sesion", "Sprint 1", "Riesgos")
        self.assertIsNotNone(session.id)
        self.assertEqual(session.title, "Nueva sesion")

        # Recuperar y actualizar
        updated_session = get_or_create_session(str(session.id), "Nuevo titulo", "Sprint 2", "Calidad")
        self.assertEqual(updated_session.id, session.id)
        self.assertEqual(updated_session.search_filter, "Sprint 2")

    def test_run_qa_pipeline_with_local_data(self):
        result = run_qa_pipeline("analisis general", "", "")
        self.assertIn("reports", result)
        self.assertIn("metrics", result)
        self.assertIn("agent_context", result)
        self.assertEqual(result["metrics"]["total"], 2)
        self.assertEqual(result["metrics"]["completed"], 1)
        self.assertEqual(result["metrics"]["blocked"], 1)
        self.assertEqual(result["metrics"]["completion_rate"], 50.0)

    def test_save_execution(self):
        session = Session.objects.create(title="Sesion Test")
        pipeline_result = run_qa_pipeline("test", "", "")
        execution = save_execution(session, pipeline_result["reports"], pipeline_result["metrics"])
        self.assertEqual(execution.session, session)
        self.assertEqual(execution.total_issues, 2)
        self.assertEqual(execution.blocked_issues, 1)

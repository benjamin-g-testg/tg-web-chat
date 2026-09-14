"""
Pruebas de Rendimiento, Escalabilidad y Casos Borde.

Cubre:
- Respuesta de endpoints bajo volumen de datos alto
- Concurrencia básica simulada con sesiones paralelas
- Campos nulos, vacíos y valores límite
- Caracteres especiales, Unicode extendido y longitudes extremas
- Robustez del pipeline ante datos de Jira mal formados
- Tiempos de respuesta dentro de umbrales aceptables
"""
import time
import uuid
import threading
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from src.database.models import Session, ChatMessage, JiraIssue, AnalysisJob
from src.agents.agent_service import JiraAgent, normalize_text
from src.core.services import run_qa_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_bulk_issues(count: int, status_val: str = "Finalizado", category: str = "done") -> None:
    """Inserta `count` JiraIssues en BD para pruebas de volumen."""
    issues = [
        JiraIssue(
            jira_id=str(9000 + i),
            issue_key=f"TATC-{9000 + i}",
            status=status_val,
            status_category=category,
            criticality="Media",
            assignee=f"Usuario {i}",
            issue_type="Task",
            description=f"Issue de volumen {i}",
        )
        for i in range(count)
    ]
    JiraIssue.objects.bulk_create(issues)


# ---------------------------------------------------------------------------
# Casos Borde de Entradas
# ---------------------------------------------------------------------------

@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class EdgeCaseInputTests(TestCase):
    """Valida la robustez del sistema ante entradas inusuales o malformadas."""

    def setUp(self):
        self.client = APIClient()
        JiraIssue.objects.create(
            jira_id="8001", issue_key="TATC-8001", status="Finalizado",
            status_category="done", criticality="Baja", assignee="Test User",
            issue_type="Task", description="Issue base",
        )

    def test_null_session_id_creates_new_session(self):
        """Un session_id nulo o vacio debe generar una sesion nueva."""
        for null_value in [None, "", "   "]:
            payload = {"message": "Analisis general", "session_id": null_value}
            response = self.client.post("/api/chat/", payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("session", response.data)
            self.assertIsNotNone(response.data["session"]["id"])

    def test_nonexistent_session_id_creates_new_session(self):
        """Un session_id con UUID inexistente debe crear una sesion nueva."""
        payload = {"message": "Analisis general", "session_id": str(uuid.uuid4())}
        response = self.client.post("/api/chat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_message_with_only_whitespace_rejected(self):
        """Mensajes de solo espacios/tabs/newlines deben rechazarse con 400."""
        for ws_input in ["   ", "\t\t", "\n\n\n", "\r\n"]:
            response = self.client.post("/api/chat/", {"message": ws_input}, format="json")
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST,
                msg=f"Se esperaba 400 para: {repr(ws_input)}"
            )

    def test_message_exactly_at_max_length_accepted(self):
        """Mensajes exactamente en el limite maximo deben ser aceptados."""
        from django.conf import settings
        max_len = getattr(settings, "MAX_MESSAGE_LENGTH", 5000)
        payload = {"message": "A" * max_len}
        response = self.client.post("/api/chat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_message_one_over_max_length_rejected(self):
        """Mensajes un caracter sobre el limite deben ser rechazados."""
        from django.conf import settings
        max_len = getattr(settings, "MAX_MESSAGE_LENGTH", 5000)
        payload = {"message": "A" * (max_len + 1)}
        response = self.client.post("/api/chat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unicode_extended_message_processed(self):
        """Mensajes con caracteres Unicode extendidos deben procesarse o ser rechazados limpiamente."""
        exotic_messages = [
            "Analisis de problemas criticos en Jira",
            "\u5206\u6790JIRA\u4e2d\u7684\u963b\u65ad\u95ee\u9898",
            "\u0410\u043d\u0430\u043b\u0438\u0437 \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0445 \u0437\u0430\u0434\u0430\u0447 Jira",
        ]
        for msg in exotic_messages:
            response = self.client.post("/api/chat/", {"message": msg}, format="json")
            self.assertNotEqual(
                response.status_code, 500,
                msg=f"El sistema no debe crashear con mensaje Unicode: {msg}"
            )

    def test_sql_injection_attempt_handled_safely(self):
        """Intentos de inyeccion SQL no deben provocar errores 500."""
        payloads = [
            "' OR '1'='1",
            "1; DROP TABLE src_session; --",
            "UNION SELECT * FROM src_jiraissue --",
        ]
        for payload_msg in payloads:
            response = self.client.post("/api/chat/", {"message": payload_msg}, format="json")
            self.assertNotEqual(
                response.status_code, 500,
                msg=f"El sistema no debe crashear ante: {payload_msg}"
            )

    def test_html_injection_sanitized(self):
        """Etiquetas HTML en mensajes deben ser escapadas; las comillas < > deben estar encodificadas."""
        injections = [
            ('<img src="x" onerror="alert(1)">Analisis', "<img"),
            ('"><svg onload=alert(1)>', "<svg"),
        ]
        for payload_msg, raw_tag in injections:
            response = self.client.post("/api/chat/", {"message": payload_msg}, format="json")
            if response.status_code == status.HTTP_201_CREATED:
                saved = ChatMessage.objects.filter(role=ChatMessage.Role.USER).last()
                if saved:
                    # La etiqueta < no debe aparecer en texto plano (debe haberse convertido a &lt;)
                    self.assertNotIn(raw_tag, saved.content,
                                     msg=f"La etiqueta HTML '{raw_tag}' no debe aparecer sin escapar")


# ---------------------------------------------------------------------------
# Pruebas de Volumen y Escalabilidad
# ---------------------------------------------------------------------------

@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class ScalabilityTests(TestCase):
    """Pruebas con grandes volumenes de datos para validar rendimiento."""

    def test_pipeline_with_100_issues(self):
        """El pipeline QA debe finalizar correctamente con 100 issues en BD."""
        _create_bulk_issues(100)
        start = time.monotonic()
        result = run_qa_pipeline("analisis general", "", "")
        elapsed = time.monotonic() - start

        self.assertIn("reports", result)
        self.assertIn("metrics", result)
        self.assertEqual(result["metrics"]["total"], 100)
        self.assertLess(elapsed, 10.0,
                        msg=f"El pipeline tardo {elapsed:.2f}s con 100 issues, umbral: 10s")

    def test_pipeline_with_500_issues(self):
        """El pipeline QA debe escalar razonablemente con 500 issues."""
        _create_bulk_issues(500)
        start = time.monotonic()
        result = run_qa_pipeline("analisis de riesgos y bloqueos", "", "")
        elapsed = time.monotonic() - start

        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["metrics"]["total"], 500)
        self.assertLess(elapsed, 30.0,
                        msg=f"El pipeline tardo {elapsed:.2f}s con 500 issues, umbral: 30s")

    def test_session_list_endpoint_with_50_sessions(self):
        """GET /api/sessions/ debe responder en menos de 5s con 50 sesiones (umbral generoso para CI local)."""
        Session.objects.bulk_create([
            Session(title=f"Sesion de carga {i}") for i in range(50)
        ])
        client = APIClient()
        start = time.monotonic()
        response = client.get("/api/sessions/")
        elapsed = time.monotonic() - start

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 100)
        self.assertLess(elapsed, 5.0,
                        msg=f"GET /api/sessions/ tardo {elapsed:.2f}s con 50 sesiones (umbral: 5s)")

    def test_session_list_pagination_cap_at_100(self):
        """El listado de sesiones no debe retornar mas de 100 registros."""
        Session.objects.bulk_create([
            Session(title=f"Sesion extra {i}") for i in range(120)
        ])
        client = APIClient()
        response = client.get("/api/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 100)

    def test_metrics_endpoint_response_time(self):
        """GET /api/metrics/ debe responder en menos de 3s con 200 issues."""
        _create_bulk_issues(200)
        client = APIClient()
        start = time.monotonic()
        response = client.get("/api/metrics/")
        elapsed = time.monotonic() - start

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed, 3.0,
                        msg=f"GET /api/metrics/ tardo {elapsed:.2f}s con 200 issues")


# ---------------------------------------------------------------------------
# Pruebas de Concurrencia Basica
# ---------------------------------------------------------------------------

@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class ConcurrencyTests(TestCase):
    """Pruebas de sesiones y chats enviados concurrentemente."""

    def setUp(self):
        JiraIssue.objects.create(
            jira_id="7001", issue_key="TATC-7001", status="Finalizado",
            status_category="done", criticality="Media", assignee="Concurrent User",
            issue_type="Task", description="Issue para concurrencia",
        )

    def test_concurrent_session_creation(self):
        """Multiples chats concurrentes deben crear sesiones independientes sin colision."""
        results = []
        errors = []
        sessions_before = Session.objects.count()

        def send_message(thread_id: int):
            client = APIClient()
            payload = {"message": f"Analisis concurrente numero {thread_id}"}
            try:
                response = client.post("/api/chat/", payload, format="json")
                results.append(response.status_code)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=send_message, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(len(errors), 0,
                         msg=f"Errores en threads concurrentes: {errors}")
        for code in results:
            self.assertEqual(code, status.HTTP_201_CREATED,
                             msg=f"Thread retorno codigo inesperado: {code}")

        new_sessions = Session.objects.count() - sessions_before
        self.assertEqual(new_sessions, len(results),
                         msg=f"Se esperaban {len(results)} sesiones nuevas, se crearon {new_sessions}")


# ---------------------------------------------------------------------------
# Pruebas de CRUD de Sesiones (PATCH y DELETE)
# ---------------------------------------------------------------------------

@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class SessionCRUDTests(TestCase):
    """Pruebas de caja negra para las operaciones PATCH y DELETE sobre sesiones."""

    def setUp(self):
        self.client = APIClient()
        self.session = Session.objects.create(
            title="Sesion Original",
            search_filter="Sprint 5",
        )

    def test_patch_rename_session_success(self):
        """PATCH /api/sessions/<id>/ debe actualizar el titulo correctamente."""
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/",
            {"title": "Sesion Renombrada"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Sesion Renombrada")
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, "Sesion Renombrada")

    def test_patch_rename_with_empty_title_rejected(self):
        """PATCH con titulo vacio debe retornar 400."""
        for empty_title in ["", "   "]:
            response = self.client.patch(
                f"/api/sessions/{self.session.id}/",
                {"title": empty_title},
                format="json",
            )
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST,
                msg=f"Se esperaba 400 para titulo: {repr(empty_title)}"
            )

    def test_patch_rename_title_truncated_at_160(self):
        """PATCH con titulo mayor a 160 chars debe ser truncado, no rechazado."""
        long_title = "A" * 200
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/",
            {"title": long_title},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["title"]), 160)

    def test_patch_rename_with_xss_sanitized(self):
        """PATCH con titulo con XSS debe sanitizarse correctamente."""
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/",
            {"title": '<script>alert("xss")</script>Sesion'},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("<script>", response.data["title"])

    def test_patch_rename_nonexistent_session(self):
        """PATCH sobre sesion inexistente debe retornar 404."""
        response = self.client.patch(
            f"/api/sessions/{uuid.uuid4()}/",
            {"title": "Titulo"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_session_success(self):
        """DELETE /api/sessions/<id>/ debe eliminar la sesion y retornar 200."""
        session_id = str(self.session.id)
        response = self.client.delete(f"/api/sessions/{session_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Session.objects.filter(id=session_id).exists())

    def test_delete_session_cascades_messages(self):
        """Eliminar una sesion debe eliminar en cascada sus mensajes."""
        ChatMessage.objects.create(
            session=self.session, role=ChatMessage.Role.USER, content="Mensaje test"
        )
        ChatMessage.objects.create(
            session=self.session, role=ChatMessage.Role.ASSISTANT, content="Respuesta test"
        )
        self.client.delete(f"/api/sessions/{self.session.id}/")
        msg_count_after = ChatMessage.objects.filter(session_id=self.session.id).count()
        self.assertEqual(msg_count_after, 0)

    def test_delete_nonexistent_session(self):
        """DELETE sobre sesion inexistente debe retornar 404."""
        response = self.client.delete(f"/api/sessions/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Pruebas del Endpoint de Artefactos Globales
# ---------------------------------------------------------------------------

@override_settings(JIRA_DATA_SOURCE="local", AGENT_PROVIDER="mock")
class GlobalArtifactsEndpointTests(TestCase):
    """Pruebas de caja negra para GET /api/artifacts/."""

    def setUp(self):
        self.client = APIClient()
        # Limpiar jobs previos para garantizar aislamiento con --keepdb
        AnalysisJob.objects.all().delete()
        Session.objects.all().delete()

    def test_get_artifacts_empty_returns_valid_structure(self):
        """GET /api/artifacts/ sin jobs debe retornar estructura valida vacia."""
        response = self.client.get("/api/artifacts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_jobs", response.data)
        self.assertIn("inventory", response.data)
        self.assertEqual(response.data["total_jobs"], 0)
        self.assertIsInstance(response.data["inventory"], list)

    def test_get_artifacts_with_completed_job_no_artifacts(self):
        """Jobs completados sin artefactos no deben aparecer en el inventario."""
        session = Session.objects.create(title="Sesion sin artefactos")
        AnalysisJob.objects.create(
            session=session,
            request_text="Consulta sin archivos",
            status=AnalysisJob.Status.COMPLETED,
            progress=100,
            stage="completed",
            result={},
        )
        response = self.client.get("/api/artifacts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_jobs"], 0)

    def test_get_artifacts_with_completed_job_with_artifacts(self):
        """Jobs completados con artefactos deben aparecer en el inventario."""
        session = Session.objects.create(title="Sesion con artefactos")
        AnalysisJob.objects.create(
            session=session,
            request_text="Consulta con archivos",
            status=AnalysisJob.Status.COMPLETED,
            progress=100,
            stage="completed",
            result={
                "artifacts": {
                    "word": {"phase_1": "reporte_fase_1.docx"},
                    "pdf": {"phase_1": "reporte_fase_1.pdf"},
                }
            },
        )
        response = self.client.get("/api/artifacts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_jobs"], 1)
        inventory = response.data["inventory"]
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0]["session_title"], "Sesion con artefactos")
        self.assertGreaterEqual(len(inventory[0]["files"]), 1)

    def test_get_artifacts_non_completed_jobs_excluded(self):
        """Jobs en estado QUEUED o FAILED no deben aparecer en el inventario."""
        session = Session.objects.create(title="Sesion no terminada")
        AnalysisJob.objects.create(
            session=session, request_text="Job en cola",
            status=AnalysisJob.Status.QUEUED, progress=0, stage="queued",
            result={"artifacts": {"word": {"phase_1": "archivo.docx"}}},
        )
        AnalysisJob.objects.create(
            session=session, request_text="Job fallido",
            status=AnalysisJob.Status.FAILED, progress=0, stage="failed",
            result={"artifacts": {"word": {"phase_1": "archivo.docx"}}},
        )
        response = self.client.get("/api/artifacts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_jobs"], 0)


# ---------------------------------------------------------------------------
# Pruebas de Normalizacion ante Casos Limite
# ---------------------------------------------------------------------------

class NormalizationEdgeCaseTests(TestCase):
    """Valida el normalizador de texto ante casos limite extremos."""

    def test_normalize_very_long_text(self):
        """Texto muy largo debe normalizarse sin error ni timeout."""
        long_text = "incidencia bloqueada " * 1000
        start = time.monotonic()
        result = normalize_text(long_text)
        elapsed = time.monotonic() - start
        self.assertIsInstance(result, str)
        self.assertLess(elapsed, 2.0, msg="La normalizacion de texto largo tardo demasiado")

    def test_normalize_only_special_chars(self):
        """Texto con solo caracteres especiales debe retornar cadena limpia."""
        result = normalize_text("!@#$%^&*()_+=[]{}|;:',.<>?/`~")
        self.assertIsInstance(result, str)

    def test_normalize_null_equivalent_strings(self):
        """Strings que representan nulos no deben romper la normalizacion."""
        for null_like in ["None", "null", "undefined", "NaN", "false", "0"]:
            result = normalize_text(null_like)
            self.assertIsInstance(result, str)

    def test_agent_process_edge_messages(self):
        """Mensajes de un solo caracter deben manejarse sin excepciones."""
        agent = JiraAgent()
        for msg in ["?", ".", "a", "x"]:
            try:
                response = agent.process_message(msg)
                self.assertIsNotNone(response)
            except Exception as exc:
                self.fail(f"process_message lanzo excepcion para '{msg}': {exc}")

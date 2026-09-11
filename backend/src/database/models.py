"""Persistent records for conversation and QA analyses."""
import uuid
from django.db import models


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160)
    search_filter = models.TextField(blank=True)
    analysis_requested = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]


class AnalysisExecution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, related_name="executions", on_delete=models.CASCADE)
    report_fase_1 = models.TextField()
    report_fase_2 = models.TextField()
    report_fase_3 = models.TextField()
    report_conclusion = models.TextField()
    report_resumen_ejecutivo = models.TextField()
    total_issues = models.PositiveIntegerField(default=0)
    blocked_issues = models.PositiveIntegerField(default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class JiraIssue(models.Model):
    """Normalized Jira source data imported from the historical workbook."""
    jira_id = models.CharField(max_length=32, unique=True)
    issue_key = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=80, blank=True)
    status_category = models.CharField(max_length=80, blank=True)
    criticality = models.CharField(max_length=80, blank=True)
    assignee = models.CharField(max_length=160, blank=True)
    epic_key = models.CharField(max_length=64, blank=True)
    epic_name = models.CharField(max_length=255, blank=True)
    product = models.CharField(max_length=160, blank=True)
    functionality = models.CharField(max_length=255, blank=True)
    issue_type = models.CharField(max_length=80, blank=True)
    phase = models.CharField(max_length=80, blank=True)
    automation_status = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    labels = models.TextField(blank=True)
    created_at_jira = models.DateTimeField(null=True, blank=True)
    updated_at_jira = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["issue_key"]

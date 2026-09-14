from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [("database", "0002_jiraissue")]

    operations = [
        migrations.CreateModel(
            name="AnalysisJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("request_text", models.TextField()),
                ("status", models.CharField(choices=[("queued", "Queued"), ("planning", "Planning"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="queued", max_length=24)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("stage", models.CharField(default="queued", max_length=80)),
                ("selected_agent", models.CharField(blank=True, max_length=32)),
                ("execution_mode", models.CharField(default="mock", max_length=32)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jobs", to="database.session")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
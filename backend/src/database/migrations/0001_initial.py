# Generated manually to make the initial schema reproducible.
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="Session", fields=[("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("title", models.CharField(max_length=160)), ("search_filter", models.TextField(blank=True)), ("analysis_requested", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True))], options={"ordering": ["-updated_at"]}),
        migrations.CreateModel(name="ChatMessage", fields=[("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant"), ("system", "System")], max_length=12)), ("content", models.TextField()), ("timestamp", models.DateTimeField(auto_now_add=True)), ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="database.session"))], options={"ordering": ["timestamp"]}),
        migrations.CreateModel(name="AnalysisExecution", fields=[("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("report_fase_1", models.TextField()), ("report_fase_2", models.TextField()), ("report_fase_3", models.TextField()), ("report_conclusion", models.TextField()), ("report_resumen_ejecutivo", models.TextField()), ("total_issues", models.PositiveIntegerField(default=0)), ("blocked_issues", models.PositiveIntegerField(default=0)), ("completion_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)), ("created_at", models.DateTimeField(auto_now_add=True)), ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="executions", to="database.session"))]),
    ]

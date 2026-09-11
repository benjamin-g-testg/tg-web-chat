import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds the Jira source table without changing existing conversation data."""
    dependencies = [("database", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="JiraIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("jira_id", models.CharField(max_length=32, unique=True)),
                ("issue_key", models.CharField(max_length=64, unique=True)),
                ("status", models.CharField(blank=True, max_length=80)),
                ("status_category", models.CharField(blank=True, max_length=80)),
                ("criticality", models.CharField(blank=True, max_length=80)),
                ("assignee", models.CharField(blank=True, max_length=160)),
                ("epic_key", models.CharField(blank=True, max_length=64)),
                ("epic_name", models.CharField(blank=True, max_length=255)),
                ("product", models.CharField(blank=True, max_length=160)),
                ("functionality", models.CharField(blank=True, max_length=255)),
                ("issue_type", models.CharField(blank=True, max_length=80)),
                ("phase", models.CharField(blank=True, max_length=80)),
                ("automation_status", models.CharField(blank=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("labels", models.TextField(blank=True)),
                ("created_at_jira", models.DateTimeField(blank=True, null=True)),
                ("updated_at_jira", models.DateTimeField(blank=True, null=True)),
                ("imported_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["issue_key"]},
        )
    ]

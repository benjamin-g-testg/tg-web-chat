from django.urls import path
from .views import (
    AnalysisJobView,
    ChatView,
    SessionListView,
    SessionDetailView,
    GlobalArtifactsView,
    MetricsView,
    ArtifactView,
)

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("sessions/", SessionListView.as_view(), name="session-list"),
    path("sessions/<uuid:session_id>/", SessionDetailView.as_view(), name="session-detail"),
    path("artifacts/", GlobalArtifactsView.as_view(), name="global-artifacts"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
    path("jobs/<uuid:job_id>/", AnalysisJobView.as_view(), name="job-detail"),
    path("jobs/<uuid:job_id>/artifacts/<str:format_name>/<str:artifact_name>", ArtifactView.as_view(), name="artifact-download"),
]
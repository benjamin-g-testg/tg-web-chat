from django.urls import path
from .views import AnalysisJobView, ChatView, SessionListView, MetricsView

urlpatterns = [
    path("chat/", ChatView.as_view()),
    path("sessions/", SessionListView.as_view()),
    path("metrics/", MetricsView.as_view()),
    path("jobs/<uuid:job_id>/", AnalysisJobView.as_view()),
]
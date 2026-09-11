from django.urls import path
from .views import ChatView, SessionListView
urlpatterns = [path("chat/", ChatView.as_view()), path("sessions/", SessionListView.as_view())]

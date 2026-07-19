from django.urls import path

from .views import AuditLogListView

urlpatterns = [
    path("activity/", AuditLogListView.as_view(), name="activity-list"),
]

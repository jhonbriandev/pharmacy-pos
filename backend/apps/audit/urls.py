"""Rutas de auditoria."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.audit.views import AuditEventViewSet, MetaView

router = DefaultRouter()
router.register("audit-events", AuditEventViewSet, basename="audit-event")

urlpatterns = [
    *router.urls,
    path("meta/", MetaView.as_view(), name="meta"),
]

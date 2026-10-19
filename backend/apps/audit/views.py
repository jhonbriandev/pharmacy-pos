"""API de auditoria: solo lectura, siempre.

No existe ningun endpoint que permita crear, modificar o borrar eventos: los
genera el backend desde los servicios de dominio.
"""

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanReadAudit
from apps.audit.models import AuditEvent
from apps.audit.serializers import AuditEventSerializer


class AuditEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [CanReadAudit]
    filterset_fields = ("action", "actor", "entity_type")
    search_fields = ("entity_id", "actor__username")
    ordering_fields = ("created_at",)

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("actor")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        return queryset


class MetaView(APIView):
    """Version de la API y de la aplicacion, para diagnostico."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings

        return Response(
            {
                "api_version": "v1",
                "app_version": getattr(settings, "APP_VERSION", "0.1.0"),
                "timezone": settings.TIME_ZONE,
                "language": settings.LANGUAGE_CODE,
            }
        )

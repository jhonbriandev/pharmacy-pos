"""API de ventas.

Reglas de acceso:
  - Cualquier rol con permiso de venta puede crear una venta.
  - El cajero solo ve **sus propias** ventas; gerencia, regencia y auditoria ven
    todas. El filtro se aplica en el servidor, nunca por un parametro del cliente.
"""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanViewAllSales, SalesAccess
from apps.sales.models import Sale
from apps.sales.serializers import (
    ReceiptSerializer,
    SaleCreateSerializer,
    SaleSerializer,
)
from apps.sales.services import create_sale

CAN_VIEW_ALL_ROLES = CanViewAllSales.roles


def _can_view_all(user) -> bool:
    """Quien puede ver las ventas de todo el equipo."""
    return user.role in CAN_VIEW_ALL_ROLES


class SaleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Listado, detalle y creacion de ventas."""

    serializer_class = SaleSerializer
    permission_classes = [SalesAccess]
    filterset_fields = ("status",)
    ordering_fields = ("created_at", "total")
    search_fields = ("number",)

    def get_queryset(self):
        queryset = Sale.objects.select_related("created_by").prefetch_related(
            "items__lot_allocations__lot", "payments"
        )
        if not _can_view_all(self.request.user):
            queryset = queryset.filter(created_by=self.request.user)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        return queryset

    def create(self, request):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sale, created = create_sale(
            items=data["items"],
            payment=data["payment"],
            user=request.user,
            client_request_id=data["client_request_id"],
            notes=data.get("notes", ""),
        )

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            SaleSerializer(sale).data,
            status=status_code,
            headers={"X-Idempotent-Replay": "false" if created else "true"},
        )

    @action(detail=True, methods=["get"], url_path="receipt")
    def receipt(self, request, pk=None):
        """Boleta para el cliente: sin costo ni margen."""
        sale = self.get_object()
        return Response(ReceiptSerializer(sale).data)


class SaleReceiptView(APIView):
    """Acceso directo a la boleta por numero de venta.

    Util para reimprimir desde el historial sin conocer el id interno.
    """

    permission_classes = [SalesAccess]

    def get(self, request, number: str):
        queryset = Sale.objects.select_related("created_by").prefetch_related("items", "payments")
        if not _can_view_all(request.user):
            queryset = queryset.filter(created_by=request.user)
        sale = queryset.filter(number=number).first()
        if sale is None:
            return Response(
                {"error": {"code": "not_found", "message": "La venta no existe."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ReceiptSerializer(sale).data)

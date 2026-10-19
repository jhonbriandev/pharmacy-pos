"""API de inventario.

Todas las escrituras delegan en ``apps.inventory.services``. Ninguna vista toca
``Lot.current_quantity`` directamente.
"""

from datetime import timedelta

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    CanAdjustStock,
    CanViewInventory,
    IsAdmin,
    IsBackOffice,
)
from apps.inventory.models import Lot, StockEntry, StockMovement
from apps.inventory.serializers import (
    FractionationSerializer,
    LotBlockSerializer,
    LotSerializer,
    StockAdjustmentSerializer,
    StockEntryCreateSerializer,
    StockEntrySerializer,
    StockMovementSerializer,
)
from apps.inventory.services import (
    adjust_stock,
    block_lot,
    create_stock_entry,
    find_consistency_issues,
    fractionate,
    today,
)


class StockEntryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Entradas de mercaderia: se crean y se consultan, nunca se editan."""

    serializer_class = StockEntrySerializer
    permission_classes = [IsBackOffice]
    filterset_fields = ("supplier",)
    search_fields = ("supplier", "document_number")
    ordering_fields = ("received_at", "created_at")

    def get_queryset(self):
        return StockEntry.objects.select_related("created_by").prefetch_related(
            "items__product__group", "items__lot"
        )

    def create(self, request):
        serializer = StockEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        entry, created = create_stock_entry(
            supplier=data["supplier"],
            document_number=data.get("document_number", ""),
            received_at=data["received_at"],
            notes=data.get("notes", ""),
            items=data["items"],
            user=request.user,
            client_request_id=data["client_request_id"],
        )

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            StockEntrySerializer(entry).data,
            status=status_code,
            headers={"X-Idempotent-Replay": "false" if created else "true"},
        )


class StockAdjustmentView(APIView):
    """Ajuste de inventario con motivo obligatorio."""

    permission_classes = [CanAdjustStock]

    def post(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        movement = adjust_stock(
            lot_id=data["lot"].pk,
            quantity_delta=data["quantity_delta"],
            reason=data["reason"],
            notes=data.get("notes", ""),
            movement_type=data.get("movement_type"),
            user=request.user,
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class FractionationView(APIView):
    """Convierte presentaciones mayores en menores (caja -> blisteres)."""

    permission_classes = [IsBackOffice]

    def post(self, request):
        serializer = FractionationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        out_movement, in_movement = fractionate(
            source_lot_id=data["source_lot"].pk,
            quantity=data["quantity"],
            reason=data.get("reason") or "Fraccionamiento de presentacion",
            user=request.user,
        )
        return Response(
            {
                "out": StockMovementSerializer(out_movement).data,
                "in": StockMovementSerializer(in_movement).data,
            },
            status=status.HTTP_201_CREATED,
        )


class StockMovementViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Libro mayor de inventario: solo lectura, por diseno."""

    serializer_class = StockMovementSerializer
    permission_classes = [CanViewInventory]
    filterset_fields = ("movement_type", "product", "lot", "reference_type")
    search_fields = ("reason", "notes", "lot__batch_number", "product__group__name")
    ordering_fields = ("created_at", "quantity_delta")

    def get_queryset(self):
        queryset = StockMovement.objects.select_related("product__group", "lot", "created_by")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        return queryset


class LotViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Lotes con su estado y sus vencimientos."""

    serializer_class = LotSerializer
    permission_classes = [CanViewInventory]
    filterset_fields = ("product", "is_blocked")
    search_fields = ("batch_number", "product__group__name")
    ordering_fields = ("expiry_date", "current_quantity")

    def get_queryset(self):
        return Lot.objects.select_related("product__group")

    @action(detail=False, methods=["get"], url_path="expiring")
    def expiring(self, request):
        """Lotes que vencen dentro de N dias (por defecto 90).

        No incluye los ya vencidos: esos tienen su propia consulta, porque la
        accion es distinta (dar de baja, no vender primero).
        """
        try:
            within_days = int(request.query_params.get("within_days", 90))
        except ValueError:
            return Response(
                {
                    "error": {
                        "code": "invalid_parameter",
                        "message": "within_days debe ser un numero.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        start = today()
        end = start + timedelta(days=max(within_days, 0))
        lots = (
            self.get_queryset()
            .filter(
                current_quantity__gt=0,
                expiry_date__gte=start,
                expiry_date__lte=end,
            )
            .order_by("expiry_date", "id")
        )
        return Response(LotSerializer(lots, many=True).data)

    @action(detail=False, methods=["get"], url_path="expired")
    def expired(self, request):
        """Lotes ya vencidos que todavia tienen existencias."""
        lots = (
            self.get_queryset()
            .filter(current_quantity__gt=0, expiry_date__lt=today())
            .order_by("expiry_date", "id")
        )
        return Response(LotSerializer(lots, many=True).data)

    @action(detail=True, methods=["post"], url_path="block")
    def block(self, request, pk=None):
        """Bloquea un lote para que no se venda."""
        lot = self.get_object()
        serializer = LotBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lot = block_lot(
            lot_id=lot.pk, reason=serializer.validated_data["reason"], user=request.user
        )
        return Response(LotSerializer(lot).data)


class ConsistencyView(APIView):
    """Verifica que la cache de stock coincida con el libro mayor.

    Es una herramienta de diagnostico para administracion: si devuelve
    diferencias, existe un camino de escritura que se salto el servicio.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        issues = find_consistency_issues()
        return Response(
            {
                "consistent": not issues,
                "issues_count": len(issues),
                "issues": issues,
            }
        )

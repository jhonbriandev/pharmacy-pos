"""Serializers de inventario.

Ninguno de ellos escribe stock: las entradas, ajustes y fraccionamientos pasan
por ``apps.inventory.services``, que es la unica puerta de entrada.
"""

from rest_framework import serializers

from apps.catalog.models import Product
from apps.inventory.models import Lot, StockEntry, StockEntryItem, StockMovement


class LotSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.display_name", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lot
        fields = (
            "id",
            "product",
            "product_name",
            "batch_number",
            "expiry_date",
            "current_quantity",
            "cost_price",
            "is_blocked",
            "block_reason",
            "is_expired",
            "available",
        )
        read_only_fields = ("current_quantity",)


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.display_name", read_only=True)
    lot_batch = serializers.CharField(source="lot.batch_number", read_only=True)
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "created_at",
            "movement_type",
            "movement_type_display",
            "product",
            "product_name",
            "lot",
            "lot_batch",
            "quantity_delta",
            "balance_after",
            "reason",
            "notes",
            "reference_type",
            "reference_id",
            "created_by",
            "created_by_name",
        )
        read_only_fields = fields

    def get_created_by_name(self, obj: StockMovement) -> str:
        return obj.created_by.full_name if obj.created_by_id else "Sistema"


class StockEntryItemInputSerializer(serializers.Serializer):
    """Linea de entrada recibida desde el cliente."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    batch_number = serializers.CharField(max_length=64)
    expiry_date = serializers.DateField()
    quantity = serializers.IntegerField(min_value=1)
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=0)


class StockEntryCreateSerializer(serializers.Serializer):
    """Entrada de mercaderia completa.

    El ``client_request_id`` es obligatorio: es lo que hace que un doble clic o
    un reintento de red no dupliquen la mercaderia.
    """

    client_request_id = serializers.UUIDField()
    supplier = serializers.CharField(max_length=160)
    document_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    received_at = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
    items = StockEntryItemInputSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        """Rechaza el mismo lote repetido dentro de una entrada.

        Sumar dos lineas del mismo lote en la misma entrada es un error de
        captura, no un caso de negocio: es mejor avisar que sumar en silencio.
        """
        seen = set()
        for item in items:
            key = (item["product"].pk, item["batch_number"])
            if key in seen:
                raise serializers.ValidationError(
                    f"El lote {item['batch_number']} esta repetido en la entrada. "
                    "Suma las cantidades en una sola linea."
                )
            seen.add(key)
        return items


class StockEntryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.display_name", read_only=True)
    batch_number = serializers.CharField(source="lot.batch_number", read_only=True)
    expiry_date = serializers.DateField(source="lot.expiry_date", read_only=True)

    class Meta:
        model = StockEntryItem
        fields = (
            "id",
            "product",
            "product_name",
            "batch_number",
            "expiry_date",
            "quantity",
            "cost_price",
        )
        read_only_fields = fields


class StockEntrySerializer(serializers.ModelSerializer):
    items = StockEntryItemSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockEntry
        fields = (
            "id",
            "received_at",
            "supplier",
            "document_number",
            "notes",
            "items",
            "created_by",
            "created_by_name",
            "created_at",
        )
        read_only_fields = fields

    def get_created_by_name(self, obj: StockEntry) -> str:
        return obj.created_by.full_name if obj.created_by_id else "Sistema"


class StockAdjustmentSerializer(serializers.Serializer):
    """Ajuste de inventario. El motivo es obligatorio."""

    lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all())
    quantity_delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=160)
    notes = serializers.CharField(required=False, allow_blank=True)
    movement_type = serializers.ChoiceField(
        choices=[
            "AJUSTE_POSITIVO",
            "AJUSTE_NEGATIVO",
            "BAJA_VENCIMIENTO",
            "BAJA_AVERIA",
        ],
        required=False,
    )

    def validate_quantity_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("La variacion no puede ser cero.")
        return value

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("El motivo es obligatorio.")
        return value.strip()


class FractionationSerializer(serializers.Serializer):
    """Fraccionamiento: abrir una caja y convertirla en blisteres o unidades."""

    source_lot = serializers.PrimaryKeyRelatedField(queryset=Lot.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    batch_number = serializers.CharField(max_length=64)
    expiry_date = serializers.DateField()
    reason = serializers.CharField(max_length=160, required=False, allow_blank=True)


class LotBlockSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=160)

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("Indica el motivo del bloqueo.")
        return value.strip()

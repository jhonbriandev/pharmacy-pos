"""Serializers de ventas.

La boleta (``ReceiptSerializer``) es deliberadamente distinta del detalle
interno: **no incluye costo ni margen**, porque ese documento lo ve el cliente.
"""

from rest_framework import serializers

from apps.sales.models import Payment, Sale, SaleItem, SaleItemLot


class SaleItemLotSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source="lot.batch_number", read_only=True)
    expiry_date = serializers.DateField(source="lot.expiry_date", read_only=True)

    class Meta:
        model = SaleItemLot
        fields = ("id", "lot", "batch_number", "expiry_date", "quantity", "unit_cost")
        read_only_fields = fields


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(read_only=True)
    lot_allocations = SaleItemLotSerializer(many=True, read_only=True)
    margin = serializers.SerializerMethodField()

    class Meta:
        model = SaleItem
        fields = (
            "id",
            "product",
            "product_name",
            "quantity",
            "unit_price",
            "line_total",
            "unit_cost",
            "margin",
            "lot_allocations",
        )
        read_only_fields = fields

    def get_margin(self, obj: SaleItem) -> str:
        """Margen de la linea: (precio - costo) x cantidad.

        Se expone al personal autenticado segun lo aprobado (riesgo aceptado
        R-Q12), pero nunca en la boleta. Se devuelve como texto con dos
        decimales para que el frontend no reciba un float.
        """
        from decimal import Decimal

        value = (obj.unit_price - obj.unit_cost) * obj.quantity
        return str(value.quantize(Decimal("0.01")))


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "method",
            "method_display",
            "amount",
            "received_amount",
            "change_amount",
            "reference",
        )
        read_only_fields = fields


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    seller_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "number",
            "status",
            "status_display",
            "total",
            "items",
            "payments",
            "created_by",
            "seller_name",
            "created_at",
            "notes",
        )
        read_only_fields = fields

    def get_seller_name(self, obj: Sale) -> str:
        return obj.created_by.full_name if obj.created_by_id else ""


class SaleCreateItemSerializer(serializers.Serializer):
    """El cliente envia producto y cantidad. **Nunca el precio.**"""

    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class SalePaymentInputSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["EFECTIVO", "TARJETA", "TRANSFERENCIA"])
    received_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    reference = serializers.CharField(max_length=64, required=False, allow_blank=True)


class SaleCreateSerializer(serializers.Serializer):
    """Peticion de venta.

    ``client_request_id`` hace la operacion idempotente: si el navegador
    reintenta, se devuelve la venta ya creada en lugar de duplicarla.
    """

    client_request_id = serializers.UUIDField()
    items = SaleCreateItemSerializer(many=True, allow_empty=False)
    payment = SalePaymentInputSerializer()
    notes = serializers.CharField(required=False, allow_blank=True)


class ReceiptItemSerializer(serializers.ModelSerializer):
    """Linea de boleta: sin costo, sin margen, sin ids internos de lote."""

    class Meta:
        model = SaleItem
        fields = ("product_name", "quantity", "unit_price", "line_total")
        read_only_fields = fields


class ReceiptSerializer(serializers.ModelSerializer):
    """Boleta para el cliente. No es un comprobante fiscal (ver docs)."""

    items = ReceiptItemSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ("number", "created_at", "seller_name", "items", "total", "payment")
        read_only_fields = fields

    def get_seller_name(self, obj: Sale) -> str:
        return obj.created_by.full_name if obj.created_by_id else ""

    def get_payment(self, obj: Sale):
        payment = obj.payments.first()
        if payment is None:
            return None
        return {
            "method": payment.get_method_display(),
            "amount": str(payment.amount),
            "received_amount": str(payment.received_amount)
            if payment.received_amount is not None
            else None,
            "change_amount": str(payment.change_amount),
            "reference": payment.reference,
        }

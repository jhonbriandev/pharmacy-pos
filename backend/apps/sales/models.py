"""Ventas.

Una venta es una operacion atomica: venta, lineas, asignacion de lotes, pagos y
movimientos de inventario se confirman juntos o no se confirman. La logica vive
en ``apps.sales.services``, nunca en las vistas.

El precio y el costo se **congelan** en la linea: si manana cambia el precio del
producto, la venta historica sigue mostrando lo que realmente se cobro.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class SaleStatus(models.TextChoices):
    CONFIRMED = "CONFIRMADA", "Confirmada"
    VOIDED = "ANULADA", "Anulada"


class PaymentMethod(models.TextChoices):
    CASH = "EFECTIVO", "Efectivo"
    CARD = "TARJETA", "Tarjeta"
    TRANSFER = "TRANSFERENCIA", "Transferencia"


class SaleNumberSequence(models.Model):
    """Contador correlativo de ventas.

    Se bloquea con ``select_for_update`` al crear cada venta, lo que garantiza
    numeros unicos y sin huecos aunque dos cajeros vendan a la vez.
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_number = models.PositiveBigIntegerField("ultimo numero", default=0)

    class Meta:
        verbose_name = "secuencia de ventas"
        verbose_name_plural = "secuencias de ventas"

    def __str__(self) -> str:
        return f"Ultimo numero de venta: {self.last_number}"


class Sale(models.Model):
    number = models.CharField("numero", max_length=20, unique=True, editable=False)
    status = models.CharField(
        "estado",
        max_length=20,
        choices=SaleStatus.choices,
        default=SaleStatus.CONFIRMED,
        db_index=True,
    )
    total = models.DecimalField(
        "total",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    client_request_id = models.UUIDField(
        "id de peticion",
        unique=True,
        help_text="Idempotencia: evita registrar dos veces la misma venta.",
    )
    notes = models.TextField("observaciones", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name="vendedor",
    )
    created_at = models.DateTimeField("creado el", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_by", "-created_at"], name="idx_sale_user_date"),
            models.Index(fields=["status", "-created_at"], name="idx_sale_status_date"),
        ]

    def __str__(self) -> str:
        return f"Venta {self.number} · S/ {self.total}"

    @property
    def items_count(self) -> int:
        return sum(item.quantity for item in self.items.all())


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="venta",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="sale_items",
        verbose_name="producto",
    )
    product_name = models.CharField(
        "producto (historico)",
        max_length=255,
        help_text="Nombre congelado al momento de la venta.",
    )
    quantity = models.PositiveIntegerField("cantidad", validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        "precio unitario",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    line_total = models.DecimalField(
        "total de la linea",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    unit_cost = models.DecimalField(
        "costo unitario (historico)",
        max_digits=12,
        decimal_places=4,
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "linea de venta"
        verbose_name_plural = "lineas de venta"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="check_sale_item_quantity_gte_1"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product_name}"


class SaleItemLot(models.Model):
    """Cuantas unidades de una linea salieron de cada lote.

    Permite que una sola linea consuma varios lotes (FEFO) y deja rastro exacto
    de que lote se vendio.
    """

    sale_item = models.ForeignKey(
        SaleItem,
        on_delete=models.CASCADE,
        related_name="lot_allocations",
        verbose_name="linea de venta",
    )
    lot = models.ForeignKey(
        "inventory.Lot",
        on_delete=models.PROTECT,
        related_name="sale_allocations",
        verbose_name="lote",
    )
    quantity = models.PositiveIntegerField("cantidad", validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(
        "costo unitario",
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "asignacion de lote"
        verbose_name_plural = "asignaciones de lote"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="check_sale_item_lot_quantity_gte_1"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} de {self.lot}"


class Payment(TimeStampedModel):
    """Pago de una venta.

    El MVP registra un solo pago por venta, pero el modelo admite varios para
    no tener que migrar cuando se agregue pago mixto.
    """

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="venta",
    )
    method = models.CharField("medio de pago", max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField(
        "monto",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    received_amount = models.DecimalField(
        "monto recibido",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Solo para efectivo: lo que entrega el cliente.",
    )
    change_amount = models.DecimalField(
        "vuelto",
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    reference = models.CharField(
        "referencia",
        max_length=64,
        blank=True,
        help_text="Numero de operacion de la tarjeta o de la transferencia.",
    )

    class Meta:
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.get_method_display()} S/ {self.amount}"

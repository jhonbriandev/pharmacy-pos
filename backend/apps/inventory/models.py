"""Inventario: lotes, libro mayor de movimientos y entradas de mercaderia.

Regla central del proyecto: **el stock no se edita**. Es la consecuencia de un
libro mayor append-only (``StockMovement``). ``Lot.current_quantity`` es una
cache que solo actualiza ``apps.inventory.services`` dentro de una transaccion,
y existe un comando para verificar que coincide con la suma de los movimientos.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class Lot(TimeStampedModel):
    """Lote fisico de un producto, con su vencimiento y su cantidad actual."""

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="lots",
        verbose_name="producto",
    )
    batch_number = models.CharField("lote", max_length=64)
    expiry_date = models.DateField("fecha de vencimiento", db_index=True)
    current_quantity = models.PositiveIntegerField(
        "cantidad actual",
        default=0,
        help_text="Cache del libro mayor. Solo la modifica el servicio de inventario.",
    )
    cost_price = models.DecimalField(
        "costo unitario",
        max_digits=12,
        decimal_places=4,
        default=0,
        validators=[MinValueValidator(0)],
    )
    is_blocked = models.BooleanField(
        "bloqueado",
        default=False,
        help_text="Un lote bloqueado no se puede vender (cuarentena, sospecha, etc.).",
    )
    block_reason = models.CharField("motivo del bloqueo", max_length=160, blank=True)

    class Meta:
        verbose_name = "lote"
        verbose_name_plural = "lotes"
        ordering = ["expiry_date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "batch_number"], name="unique_lot_per_product_batch"
            ),
        ]
        indexes = [
            models.Index(
                fields=["product", "expiry_date", "is_blocked"],
                name="idx_lot_fefo",
            ),
            models.Index(fields=["expiry_date", "current_quantity"], name="idx_lot_expiry_qty"),
        ]

    def __str__(self) -> str:
        return f"{self.product} · lote {self.batch_number} · vence {self.expiry_date:%d/%m/%Y}"


class MovementType(models.TextChoices):
    ENTRY = "ENTRADA", "Entrada de mercaderia"
    SALE = "SALIDA_VENTA", "Salida por venta"
    ADJUSTMENT_IN = "AJUSTE_POSITIVO", "Ajuste positivo"
    ADJUSTMENT_OUT = "AJUSTE_NEGATIVO", "Ajuste negativo"
    EXPIRY = "BAJA_VENCIMIENTO", "Baja por vencimiento"
    DAMAGE = "BAJA_AVERIA", "Baja por averia"
    FRACTIONATION_OUT = "FRACCIONAMIENTO_SALIDA", "Fraccionamiento (salida)"
    FRACTIONATION_IN = "FRACCIONAMIENTO_ENTRADA", "Fraccionamiento (entrada)"


class ReferenceType(models.TextChoices):
    SALE = "VENTA", "Venta"
    STOCK_ENTRY = "ENTRADA", "Entrada de mercaderia"
    ADJUSTMENT = "AJUSTE", "Ajuste de inventario"
    FRACTIONATION = "FRACCIONAMIENTO", "Fraccionamiento"
    MANUAL = "MANUAL", "Manual"


class StockMovement(models.Model):
    """Movimiento de inventario, inmutable.

    No usa ``TimeStampedModel`` a proposito: un movimiento no se actualiza.
    La referencia al documento de origen es generica (tipo + id) para evitar
    una dependencia circular entre ``inventory`` y ``sales``.
    """

    lot = models.ForeignKey(
        Lot,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="lote",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="producto",
    )
    movement_type = models.CharField(
        "tipo de movimiento",
        max_length=32,
        choices=MovementType.choices,
        db_index=True,
    )
    quantity_delta = models.IntegerField(
        "variacion",
        help_text="Positivo para entradas, negativo para salidas.",
    )
    balance_after = models.PositiveIntegerField(
        "saldo del lote despues del movimiento",
    )
    reason = models.CharField("motivo", max_length=160, blank=True)
    notes = models.TextField("observaciones", blank=True)
    reference_type = models.CharField(
        "tipo de referencia",
        max_length=20,
        choices=ReferenceType.choices,
        blank=True,
    )
    reference_id = models.PositiveBigIntegerField(
        "id de referencia",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="registrado por",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("creado el", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="check_movement_quantity_not_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "-created_at"], name="idx_movement_product_date"),
            models.Index(fields=["reference_type", "reference_id"], name="idx_movement_reference"),
        ]

    def __str__(self) -> str:
        sign = "+" if self.quantity_delta > 0 else ""
        return f"{self.get_movement_type_display()} {sign}{self.quantity_delta} · {self.lot}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Los movimientos de inventario son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los movimientos de inventario no se pueden eliminar.")


class StockEntry(TimeStampedModel):
    """Documento de entrada de mercaderia (recepcion de un proveedor)."""

    supplier = models.CharField("proveedor", max_length=160)
    document_number = models.CharField("numero de documento", max_length=64, blank=True)
    received_at = models.DateField("fecha de recepcion")
    notes = models.TextField("observaciones", blank=True)
    client_request_id = models.UUIDField(
        "id de peticion",
        unique=True,
        help_text="Evita registrar la misma entrada dos veces.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_entries",
        verbose_name="registrado por",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "entrada de mercaderia"
        verbose_name_plural = "entradas de mercaderia"
        ordering = ["-received_at", "-id"]

    def __str__(self) -> str:
        return f"Entrada {self.received_at:%d/%m/%Y} · {self.supplier}"


class StockEntryItem(models.Model):
    """Linea de una entrada: producto, lote y cantidad recibida."""

    entry = models.ForeignKey(
        StockEntry,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="entrada",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="entry_items",
        verbose_name="producto",
    )
    lot = models.ForeignKey(
        Lot,
        on_delete=models.PROTECT,
        related_name="entry_items",
        verbose_name="lote",
    )
    quantity = models.PositiveIntegerField("cantidad", validators=[MinValueValidator(1)])
    cost_price = models.DecimalField(
        "costo unitario",
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "linea de entrada"
        verbose_name_plural = "lineas de entrada"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product}"

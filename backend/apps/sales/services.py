"""Servicio transaccional de ventas: el nucleo del punto de venta.

Garantias que ofrece ``create_sale``:

1. **Atomicidad.** Venta, lineas, asignacion de lotes, movimientos de inventario
   y pago se confirman juntos. Si algo falla, no queda ni rastro.
2. **FEFO.** Los lotes se consumen del que vence primero al que vence despues.
3. **Sin stock negativo.** Si no alcanza, se rechaza con el detalle del
   conflicto (nunca se descuenta parcialmente).
4. **Precio del servidor.** El cliente nunca envia precios: se leen del catalogo
   en el momento de la venta y se congelan en la linea.
5. **Idempotencia.** Repetir el mismo ``client_request_id`` devuelve la venta ya
   creada en lugar de duplicarla.

Orden de bloqueos (para evitar deadlocks): primero la secuencia de numeracion,
despues los lotes en un solo orden (por id ascendente).
"""

from __future__ import annotations

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.catalog.models import Product
from apps.common.money import ZERO, money
from apps.common.money import unit_cost as round_unit_cost
from apps.inventory.exceptions import InsufficientStock
from apps.inventory.models import MovementType, ReferenceType
from apps.inventory.services import apply_movement, lock_sellable_lots
from apps.sales.exceptions import InsufficientPayment, ProductNotAvailable
from apps.sales.models import (
    Payment,
    PaymentMethod,
    Sale,
    SaleItem,
    SaleItemLot,
    SaleNumberSequence,
)

MAX_PRODUCT_NAME = 255


def _next_sale_number() -> str:
    """Reserva el siguiente numero correlativo de venta.

    La fila de la secuencia se bloquea con ``select_for_update``, de modo que dos
    cajeros que venden a la vez obtienen numeros distintos y consecutivos. Es
    deliberadamente serializante: la alternativa (secuencias sin bloqueo) deja
    huecos o numeros repetidos, y aqui la correccion importa mas que el caudal.

    El primer uso crea la fila; si dos procesos lo intentan a la vez, uno falla
    con ``IntegrityError`` y se reintenta leyendo la fila ya creada.
    """
    try:
        sequence = SaleNumberSequence.objects.select_for_update().get(pk=1)
    except SaleNumberSequence.DoesNotExist:
        try:
            with transaction.atomic():
                SaleNumberSequence.objects.create(pk=1, last_number=0)
        except IntegrityError:
            pass  # otro proceso la creo: se lee abajo
        sequence = SaleNumberSequence.objects.select_for_update().get(pk=1)

    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])
    return f"{sequence.last_number:08d}"


def _normalize_items(items: list[dict]) -> list[dict]:
    """Consolida lineas repetidas del mismo producto.

    Si el cajero escanea dos veces el mismo producto, se vende una sola linea
    con la cantidad sumada: es lo que espera y evita asignaciones duplicadas.
    """
    quantities: dict[int, int] = {}
    order: list[int] = []
    for item in items:
        product_id = int(item["product_id"])
        quantity = int(item["quantity"])
        if quantity < 1:
            raise ValidationError("La cantidad de cada producto debe ser al menos 1.")
        if product_id not in quantities:
            quantities[product_id] = 0
            order.append(product_id)
        quantities[product_id] += quantity
    return [{"product_id": pid, "quantity": quantities[pid]} for pid in order]


@transaction.atomic
def create_sale(
    *,
    items: list[dict],
    payment: dict,
    user,
    client_request_id,
    notes: str = "",
) -> tuple[Sale, bool]:
    """Registra una venta. Devuelve ``(venta, creada)``."""
    # --- Idempotencia -------------------------------------------------------
    existing = Sale.objects.filter(client_request_id=client_request_id).first()
    if existing is not None:
        return existing, False

    normalized = _normalize_items(items)
    if not normalized:
        raise ValidationError("La venta debe incluir al menos un producto.")

    # --- Productos ----------------------------------------------------------
    product_ids = [item["product_id"] for item in normalized]
    products = {
        product.pk: product
        for product in Product.objects.select_related("group").filter(
            pk__in=product_ids, is_active=True
        )
    }
    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise ProductNotAvailable(
            "Hay productos inexistentes o inactivos en la venta.",
            details={"product_ids": missing},
        )

    # --- Numeracion y bloqueo de lotes --------------------------------------
    number = _next_sale_number()
    lots = lock_sellable_lots(product_ids)
    lots_by_product: dict[int, list] = defaultdict(list)
    for lot in lots:
        lots_by_product[lot.product_id].append(lot)
    for product_lots in lots_by_product.values():
        # Dentro de cada producto, se consume primero lo que antes vence.
        product_lots.sort(key=lambda lot: (lot.expiry_date, lot.pk))

    # --- Asignacion FEFO ----------------------------------------------------
    lines: list[dict] = []
    total = ZERO
    for item in normalized:
        product_id = item["product_id"]
        quantity = item["quantity"]
        product = products[product_id]

        remaining = quantity
        allocations: list[dict] = []
        for lot in lots_by_product.get(product_id, []):
            if remaining <= 0:
                break
            take = min(remaining, lot.current_quantity)
            if take <= 0:
                continue
            allocations.append({"lot": lot, "quantity": take})
            remaining -= take

        if remaining > 0:
            available = sum(allocation["quantity"] for allocation in allocations)
            raise InsufficientStock(
                f"No hay stock suficiente de {product}. "
                f"Disponible: {available}, solicitado: {quantity}.",
                details={
                    "product_id": product_id,
                    "product": str(product),
                    "available": available,
                    "requested": quantity,
                },
            )

        line_total = money(product.sale_price * quantity)
        total = money(total + line_total)
        lines.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
                "allocations": allocations,
            }
        )

    # --- Pago ---------------------------------------------------------------
    method = payment["method"]
    if method not in PaymentMethod.values:
        raise ValidationError("El medio de pago no es valido.")

    received = payment.get("received_amount")
    if method == PaymentMethod.CASH:
        received = money(received if received is not None else total)
        if received < 0:
            raise ValidationError("El monto recibido no puede ser negativo.")
        if received < total:
            raise InsufficientPayment(
                "El monto recibido es menor que el total de la venta.",
                details={"total": str(total), "received": str(received)},
            )
        change = money(received - total)
    else:
        if received is not None:
            raise ValidationError("Solo el pago en efectivo admite monto recibido.")
        received = None
        change = ZERO

    # --- Persistencia -------------------------------------------------------
    sale = Sale.objects.create(
        number=number,
        total=total,
        client_request_id=client_request_id,
        created_by=user,
        notes=notes,
    )

    for line in lines:
        product = line["product"]
        quantity = line["quantity"]

        weighted_cost = sum(
            (
                allocation["lot"].cost_price * allocation["quantity"]
                for allocation in line["allocations"]
            ),
            ZERO,
        )
        unit_cost_value = round_unit_cost(weighted_cost / quantity)

        sale_item = SaleItem.objects.create(
            sale=sale,
            product=product,
            product_name=str(product)[:MAX_PRODUCT_NAME],
            quantity=quantity,
            unit_price=product.sale_price,
            line_total=line["line_total"],
            unit_cost=unit_cost_value,
        )

        for allocation in line["allocations"]:
            lot = allocation["lot"]
            SaleItemLot.objects.create(
                sale_item=sale_item,
                lot=lot,
                quantity=allocation["quantity"],
                unit_cost=lot.cost_price,
            )
            apply_movement(
                lot=lot,
                movement_type=MovementType.SALE,
                quantity_delta=-allocation["quantity"],
                user=user,
                reason=f"Venta {number}",
                reference_type=ReferenceType.SALE,
                reference_id=sale.pk,
            )

    Payment.objects.create(
        sale=sale,
        method=method,
        amount=total,
        received_amount=received,
        change_amount=change,
        reference=payment.get("reference", "") or "",
    )

    record_event(
        action=AuditAction.SALE_CREATED,
        entity=sale,
        actor=user,
        after={
            "number": number,
            "total": str(total),
            "lines": len(lines),
            "payment_method": method,
        },
    )
    return sale, True

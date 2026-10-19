"""Servicios de dominio de inventario.

**Esta es la unica puerta de entrada al stock.** Ninguna vista, serializer ni
tarea escribe ``Lot.current_quantity`` ni crea ``StockMovement`` por su cuenta.
Si esa regla se rompe, la verificacion de consistencia lo detectara.

Reglas que implementa:
  - El saldo de un lote es la suma de sus movimientos (libro mayor).
  - Un lote vence al final de su fecha: es vendible ese dia y no despues.
  - Un lote bloqueado nunca se vende.
  - El stock no puede quedar negativo (ademas de la restriccion en la base).
  - El fraccionamiento genera dos movimientos en la misma transaccion.
"""

from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.catalog.models import Product, UnitConversion
from apps.common.money import unit_cost as round_unit_cost
from apps.inventory.exceptions import (
    InsufficientStock,
    InvalidConversion,
    LotBlocked,
    LotExpired,
    LotExpiryMismatch,
)
from apps.inventory.models import (
    Lot,
    MovementType,
    ReferenceType,
    StockEntry,
    StockEntryItem,
    StockMovement,
)


def today() -> date:
    """Fecha actual en la zona horaria del negocio (America/Lima)."""
    return timezone.localdate()


def is_expired(lot: Lot, *, on_date: date | None = None) -> bool:
    """Un lote vence al final de su fecha: el mismo dia todavia es vendible."""
    return lot.expiry_date < (on_date or today())


def sellable_lots(product: Product, *, on_date: date | None = None):
    """Lotes vendibles de un producto, en orden FEFO.

    FEFO = primero en expirar, primero en salir.
    """
    return Lot.objects.filter(
        product=product,
        is_blocked=False,
        current_quantity__gt=0,
        expiry_date__gte=on_date or today(),
    ).order_by("expiry_date", "id")


def lock_sellable_lots(product_ids, *, on_date: date | None = None) -> list[Lot]:
    """Bloquea los lotes vendibles de varios productos y los devuelve.

    Se bloquea **en un solo orden** (por id ascendente) para que dos ventas
    concurrentes nunca se bloqueen mutuamente en distinto orden: eso es lo que
    producira deadlocks.
    """
    return list(
        Lot.objects.select_for_update()
        .filter(
            product_id__in=list(product_ids),
            is_blocked=False,
            current_quantity__gt=0,
            expiry_date__gte=on_date or today(),
        )
        .order_by("id")
    )


def apply_movement(
    *,
    lot: Lot,
    movement_type: str,
    quantity_delta: int,
    user=None,
    reason: str = "",
    notes: str = "",
    reference_type: str = "",
    reference_id: int | None = None,
) -> StockMovement:
    """Aplica un movimiento a un lote y lo registra en el libro mayor.

    Debe llamarse **dentro de una transaccion** y con el lote ya bloqueado con
    ``select_for_update`` si puede haber concurrencia.
    """
    if quantity_delta == 0:
        raise ValidationError("Un movimiento debe tener una cantidad distinta de cero.")

    new_quantity = lot.current_quantity + quantity_delta
    if new_quantity < 0:
        raise InsufficientStock(
            f"El lote {lot.batch_number} de {lot.product} solo tiene "
            f"{lot.current_quantity} unidades disponibles.",
            details={
                "lot_id": lot.pk,
                "batch_number": lot.batch_number,
                "available": lot.current_quantity,
                "requested": -quantity_delta,
            },
        )

    lot.current_quantity = new_quantity
    lot.save(update_fields=["current_quantity", "updated_at"])

    return StockMovement.objects.create(
        lot=lot,
        product=lot.product,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        balance_after=new_quantity,
        reason=reason,
        notes=notes,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=user,
    )


def _get_or_create_lot(
    *,
    product: Product,
    batch_number: str,
    expiry_date: date,
    cost_price,
) -> tuple[Lot, bool]:
    """Obtiene el lote y lo crea si no existe, de forma segura ante concurrencia."""
    try:
        lot = Lot.objects.select_for_update().get(product=product, batch_number=batch_number)
    except Lot.DoesNotExist:
        try:
            lot = Lot.objects.create(
                product=product,
                batch_number=batch_number,
                expiry_date=expiry_date,
                cost_price=cost_price,
                current_quantity=0,
            )
            return lot, True
        except IntegrityError:
            # Otra transaccion lo creo entre el get y el create.
            lot = Lot.objects.select_for_update().get(product=product, batch_number=batch_number)

    if lot.expiry_date != expiry_date:
        raise LotExpiryMismatch(
            f"El lote {batch_number} de {product} ya esta registrado con "
            f"vencimiento {lot.expiry_date:%d/%m/%Y}.",
            details={
                "lot_id": lot.pk,
                "registered_expiry": lot.expiry_date.isoformat(),
                "provided_expiry": expiry_date.isoformat(),
            },
        )
    return lot, False


@transaction.atomic
def create_stock_entry(
    *,
    supplier: str,
    received_at: date,
    items: list[dict],
    user=None,
    client_request_id,
    document_number: str = "",
    notes: str = "",
) -> tuple[StockEntry, bool]:
    """Registra una entrada de mercaderia.

    Es idempotente respecto de ``client_request_id``: si el navegador reintenta
    la misma peticion, no se duplica la entrada.

    ``items`` es una lista de diccionarios con:
        product, batch_number, expiry_date, quantity, cost_price
    """
    if not items:
        raise ValidationError("La entrada debe tener al menos un producto.")

    entry, created = StockEntry.objects.get_or_create(
        client_request_id=client_request_id,
        defaults={
            "supplier": supplier,
            "document_number": document_number,
            "received_at": received_at,
            "notes": notes,
            "created_by": user,
        },
    )
    if not created:
        return entry, False

    for item in items:
        product: Product = item["product"]
        quantity = int(item["quantity"])
        cost_price = round_unit_cost(item["cost_price"])
        if quantity <= 0:
            raise ValidationError("La cantidad recibida debe ser mayor que cero.")

        lot, _ = _get_or_create_lot(
            product=product,
            batch_number=item["batch_number"],
            expiry_date=item["expiry_date"],
            cost_price=cost_price,
        )

        # El costo del lote y del producto se actualizan con la ultima compra.
        lot.cost_price = cost_price
        lot.save(update_fields=["cost_price", "updated_at"])
        Product.objects.filter(pk=product.pk).update(last_cost=cost_price)
        product.last_cost = cost_price

        StockEntryItem.objects.create(
            entry=entry,
            product=product,
            lot=lot,
            quantity=quantity,
            cost_price=cost_price,
        )

        apply_movement(
            lot=lot,
            movement_type=MovementType.ENTRY,
            quantity_delta=quantity,
            user=user,
            reason=f"Entrada de mercaderia · {supplier}",
            notes=document_number,
            reference_type=ReferenceType.STOCK_ENTRY,
            reference_id=entry.pk,
        )

    record_event(
        action=AuditAction.STOCK_ENTRY_CREATED,
        entity=entry,
        actor=user,
        after={
            "supplier": supplier,
            "document_number": document_number,
            "received_at": received_at.isoformat(),
            "items": len(items),
        },
    )
    return entry, True


@transaction.atomic
def adjust_stock(
    *,
    lot_id: int,
    quantity_delta: int,
    reason: str,
    user=None,
    notes: str = "",
    movement_type: str | None = None,
) -> StockMovement:
    """Ajuste manual de stock. El motivo es obligatorio.

    Los ajustes no se editan ni se borran: se corrigen con otro movimiento.
    """
    if not reason or not reason.strip():
        raise ValidationError("El motivo del ajuste es obligatorio.")

    lot = Lot.objects.select_for_update().get(pk=lot_id)
    if movement_type is None:
        movement_type = (
            MovementType.ADJUSTMENT_IN if quantity_delta > 0 else MovementType.ADJUSTMENT_OUT
        )

    movement = apply_movement(
        lot=lot,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        user=user,
        reason=reason,
        notes=notes,
        reference_type=ReferenceType.ADJUSTMENT,
        reference_id=lot.pk,
    )

    record_event(
        action=AuditAction.STOCK_ADJUSTMENT,
        entity=lot,
        actor=user,
        before={"current_quantity": lot.current_quantity - quantity_delta},
        after={"current_quantity": lot.current_quantity},
        request=None,
    )
    return movement


@transaction.atomic
def block_lot(*, lot_id: int, reason: str, user=None) -> Lot:
    """Bloquea un lote (cuarentena). No se elimina: se bloquea."""
    lot = Lot.objects.select_for_update().get(pk=lot_id)
    lot.is_blocked = True
    lot.block_reason = reason[:160]
    lot.save(update_fields=["is_blocked", "block_reason", "updated_at"])

    record_event(
        action=AuditAction.LOT_BLOCKED,
        entity=lot,
        actor=user,
        after={"is_blocked": True, "reason": reason},
    )
    return lot


@transaction.atomic
def fractionate(
    *,
    source_lot_id: int,
    quantity: int,
    user=None,
    reason: str = "Fraccionamiento de presentacion",
) -> tuple[StockMovement, StockMovement]:
    """Abre una presentacion mayor y la convierte en la menor configurada.

    Reglas de fraccionamiento (RF), fijadas con la farmacia:

    RF1. Solo se fracciona un lote **vendible**: ni bloqueado ni vencido.
         Abrir un lote vencido y vender sus unidades "blanquearia" el
         vencimiento, que es justo lo que el sistema debe impedir.
    RF2. La conversion va siempre de la presentacion mayor a la menor que
         declare ``UnitConversion`` (factor >= 2), dentro del mismo grupo de
         producto, y la presentacion destino debe estar activa.
    RF3. La cantidad es un entero mayor que cero y no puede superar el stock
         actual del lote de origen.
    RF4. El lote destino **hereda** el numero de lote y el vencimiento del
         origen: es el mismo producto fisico. No se piden al usuario ni se
         pueden inventar; sin esto no hay trazabilidad.
    RF5. Si el lote destino ya existe (misma presentacion, mismo lote), se le
         suma la cantidad; nunca se crea un duplicado.
    RF6. El costo unitario del destino es el del origen dividido por el factor.
         El costo del origen no cambia.
    RF7. Genera dos movimientos en la misma transaccion (salida y entrada) y un
         evento de auditoria. Es **un solo paso**: caja -> blister y
         blister -> unidad son dos operaciones distintas, cada una auditada.

    Ejemplo: 1 caja de 10 blisters -> sale 1 caja, entran 10 blisters, con el
    mismo lote y el mismo vencimiento.
    """
    if quantity <= 0:
        raise ValidationError("La cantidad a fraccionar debe ser mayor que cero.")

    source_lot = (
        Lot.objects.select_for_update().select_related("product__group").get(pk=source_lot_id)
    )

    # RF1
    if source_lot.is_blocked:
        raise LotBlocked(
            f"El lote {source_lot.batch_number} esta bloqueado y no se puede fraccionar.",
            details={"lot_id": source_lot.pk, "reason": source_lot.block_reason},
        )
    if is_expired(source_lot):
        raise LotExpired(
            f"El lote {source_lot.batch_number} esta vencido y no se puede fraccionar.",
            details={"lot_id": source_lot.pk, "expiry_date": source_lot.expiry_date.isoformat()},
        )

    # RF2
    conversion = (
        UnitConversion.objects.select_related("target")
        .filter(source=source_lot.product, group_id=source_lot.product.group_id)
        .order_by("id")
        .first()
    )
    if conversion is None:
        raise InvalidConversion(
            f"{source_lot.product} no tiene una conversion de presentacion definida.",
            details={"product_id": source_lot.product_id},
        )

    target_product = conversion.target
    if target_product.group_id != source_lot.product.group_id:
        raise InvalidConversion(
            "La conversion cruza grupos de producto: revisa el catalogo.",
            details={"conversion_id": conversion.pk},
        )
    if not target_product.is_active:
        raise InvalidConversion(
            f"La presentacion destino ({target_product}) esta inactiva.",
            details={"product_id": target_product.pk},
        )

    # RF3
    if quantity > source_lot.current_quantity:
        raise InsufficientStock(
            f"El lote {source_lot.batch_number} solo tiene "
            f"{source_lot.current_quantity} unidades del origen.",
            details={
                "lot_id": source_lot.pk,
                "batch_number": source_lot.batch_number,
                "available": source_lot.current_quantity,
                "requested": quantity,
            },
        )

    units = quantity * conversion.factor
    target_cost = round_unit_cost(source_lot.cost_price / conversion.factor)

    # RF4 y RF5
    target_lot, _ = _get_or_create_lot(
        product=target_product,
        batch_number=source_lot.batch_number,
        expiry_date=source_lot.expiry_date,
        cost_price=target_cost,
    )

    out_movement = apply_movement(
        lot=source_lot,
        movement_type=MovementType.FRACTIONATION_OUT,
        quantity_delta=-quantity,
        user=user,
        reason=reason,
        reference_type=ReferenceType.FRACTIONATION,
        reference_id=target_lot.pk,
    )
    in_movement = apply_movement(
        lot=target_lot,
        movement_type=MovementType.FRACTIONATION_IN,
        quantity_delta=units,
        user=user,
        reason=reason,
        reference_type=ReferenceType.FRACTIONATION,
        reference_id=source_lot.pk,
    )

    record_event(
        action=AuditAction.FRACTIONATION,
        entity=source_lot,
        actor=user,
        after={
            "source_lot": source_lot.pk,
            "source_product": source_lot.product_id,
            "quantity": quantity,
            "target_lot": target_lot.pk,
            "target_product": target_product.pk,
            "units": units,
            "factor": conversion.factor,
        },
    )
    return out_movement, in_movement


def product_stock(product: Product, *, on_date: date | None = None) -> int:
    """Stock disponible (solo lotes vendibles) de un producto."""
    result = sellable_lots(product, on_date=on_date).aggregate(total=Sum("current_quantity"))
    return result["total"] or 0


def sellable_stock_expression(*, on_date: date | None = None):
    """Expresion SQL de stock vendible, para anotar un queryset de productos.

    Se resuelve en la base de datos para evitar una consulta por producto en
    los listados y en las alertas de stock bajo.
    """
    return Sum(
        "lots__current_quantity",
        filter=Q(
            lots__is_blocked=False,
            lots__expiry_date__gte=on_date or today(),
        ),
        default=0,
    )


def find_consistency_issues() -> list[dict]:
    """Compara la cache de cada lote con la suma de su libro mayor.

    Deberia devolver siempre una lista vacia. Si algo aparece aqui, existe un
    camino de escritura que se salto ``apply_movement``.
    """
    issues: list[dict] = []
    lots = Lot.objects.annotate(ledger_quantity=Sum("movements__quantity_delta"))
    for lot in lots.iterator():
        ledger = lot.ledger_quantity or 0
        if ledger != lot.current_quantity:
            issues.append(
                {
                    "lot_id": lot.pk,
                    "product": str(lot.product),
                    "batch_number": lot.batch_number,
                    "cached": lot.current_quantity,
                    "ledger": ledger,
                    "difference": lot.current_quantity - ledger,
                }
            )
    return issues

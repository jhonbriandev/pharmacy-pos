"""Pruebas del nucleo: FEFO, vencimientos, stock y atomicidad."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from apps.inventory.exceptions import InsufficientStock, LotExpiryMismatch
from apps.inventory.models import Lot, MovementType, StockMovement
from apps.inventory.services import (
    adjust_stock,
    create_stock_entry,
    fractionate,
    is_expired,
    sellable_lots,
    today,
)
from apps.sales.exceptions import InsufficientPayment
from apps.sales.models import Sale, SaleItemLot
from apps.sales.services import create_sale

pytestmark = pytest.mark.django_db


def cash_payment(amount="100.00"):
    return {"method": "EFECTIVO", "received_amount": Decimal(amount)}


# ---------------------------------------------------------------------------
# Vencimientos (Q2: un lote vence al final de su fecha)
# ---------------------------------------------------------------------------


def test_lot_expiring_today_is_still_sellable(lot_factory):
    lot = lot_factory(days_to_expiry=0, quantity=5)
    assert is_expired(lot) is False
    assert list(sellable_lots(lot.product)) == [lot]


def test_lot_expired_yesterday_is_not_sellable(lot_factory):
    lot = lot_factory(days_to_expiry=-1, quantity=5)
    assert is_expired(lot) is True
    assert list(sellable_lots(lot.product)) == []


def test_blocked_lot_is_not_sellable(lot_factory):
    lot = lot_factory(days_to_expiry=30, quantity=5)
    lot.is_blocked = True
    lot.save(update_fields=["is_blocked"])
    assert list(sellable_lots(lot.product)) == []


def test_expired_lot_cannot_be_sold(lot_factory, cashier_user):
    lot = lot_factory(days_to_expiry=-1, quantity=5)

    with pytest.raises(InsufficientStock):
        create_sale(
            items=[{"product_id": lot.product_id, "quantity": 1}],
            payment=cash_payment(),
            user=cashier_user,
            client_request_id=uuid4(),
        )
    assert lot.current_quantity == 5


# ---------------------------------------------------------------------------
# FEFO
# ---------------------------------------------------------------------------


def test_fefo_consumes_the_soonest_expiring_lot_first(lot_factory, cashier_user):
    later = lot_factory(days_to_expiry=200, quantity=10, batch="TARDE")
    sooner = lot_factory(days_to_expiry=30, quantity=10, batch="PRONTO")

    sale, _ = create_sale(
        items=[{"product_id": sooner.product_id, "quantity": 6}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=uuid4(),
    )

    sooner.refresh_from_db()
    later.refresh_from_db()
    assert sooner.current_quantity == 4
    assert later.current_quantity == 10

    allocation = SaleItemLot.objects.get(sale_item__sale=sale)
    assert allocation.lot_id == sooner.pk
    assert allocation.quantity == 6


def test_fefo_spans_multiple_lots_when_needed(lot_factory, cashier_user):
    sooner = lot_factory(days_to_expiry=10, quantity=3, batch="A")
    later = lot_factory(days_to_expiry=100, quantity=10, batch="B")

    sale, _ = create_sale(
        items=[{"product_id": sooner.product_id, "quantity": 5}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=uuid4(),
    )

    sooner.refresh_from_db()
    later.refresh_from_db()
    assert sooner.current_quantity == 0
    assert later.current_quantity == 8

    allocations = SaleItemLot.objects.filter(sale_item__sale=sale).order_by("lot__expiry_date")
    assert [(a.lot_id, a.quantity) for a in allocations] == [(sooner.pk, 3), (later.pk, 2)]


def test_duplicate_product_lines_are_consolidated(stocked_lot, cashier_user):
    sale, _ = create_sale(
        items=[
            {"product_id": stocked_lot.product_id, "quantity": 2},
            {"product_id": stocked_lot.product_id, "quantity": 3},
        ],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=uuid4(),
    )

    assert sale.items.count() == 1
    assert sale.items.first().quantity == 5
    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 5


# ---------------------------------------------------------------------------
# Integridad del stock
# ---------------------------------------------------------------------------


def test_sale_rejects_more_than_available_and_writes_nothing(lot_factory, cashier_user):
    lot = lot_factory(days_to_expiry=50, quantity=3)

    with pytest.raises(InsufficientStock) as exc:
        create_sale(
            items=[{"product_id": lot.product_id, "quantity": 4}],
            payment=cash_payment(),
            user=cashier_user,
            client_request_id=uuid4(),
        )

    assert exc.value.business_details["available"] == 3
    assert exc.value.business_details["requested"] == 4
    assert Sale.objects.count() == 0
    # El unico movimiento es la carga inicial del fixture: no se genero
    # ningun movimiento de venta ni descuento parcial.
    assert StockMovement.objects.filter(movement_type=MovementType.SALE).count() == 0
    lot.refresh_from_db()
    assert lot.current_quantity == 3


def test_stock_never_goes_negative_at_the_database_level(stocked_lot):
    from django.db import IntegrityError

    stocked_lot.current_quantity = -1
    with pytest.raises(IntegrityError):
        stocked_lot.save()


def test_movements_are_immutable(stocked_lot, cashier_user):
    movement = StockMovement.objects.create(
        lot=stocked_lot,
        product=stocked_lot.product,
        movement_type=MovementType.ADJUSTMENT_IN,
        quantity_delta=1,
        balance_after=11,
        created_by=cashier_user,
    )

    movement.quantity_delta = 5
    with pytest.raises(ValidationError):
        movement.save()

    with pytest.raises(ValidationError):
        movement.delete()


# ---------------------------------------------------------------------------
# Idempotencia
# ---------------------------------------------------------------------------


def test_same_client_request_id_does_not_duplicate_the_sale(stocked_lot, cashier_user):
    request_id = uuid4()

    first, created_first = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 2}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=request_id,
    )
    second, created_second = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 2}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=request_id,
    )

    assert created_first is True
    assert created_second is False
    assert first.pk == second.pk
    assert Sale.objects.count() == 1
    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 8


# ---------------------------------------------------------------------------
# Precio congelado
# ---------------------------------------------------------------------------


def test_price_is_frozen_in_the_sale_line(stocked_lot, cashier_user):
    sale, _ = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 1}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=uuid4(),
    )

    product = stocked_lot.product
    product.sale_price = Decimal("99.00")
    product.save(update_fields=["sale_price"])

    item = sale.items.first()
    item.refresh_from_db()
    assert item.unit_price == Decimal("12.00")
    assert sale.total == Decimal("12.00")


def test_total_uses_decimal_arithmetic(stocked_lot, cashier_user):
    sale, _ = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 3}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=uuid4(),
    )
    assert sale.total == Decimal("36.00")


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------


def test_cash_payment_returns_change(stocked_lot, cashier_user):
    sale, _ = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 1}],
        payment={"method": "EFECTIVO", "received_amount": Decimal("20.00")},
        user=cashier_user,
        client_request_id=uuid4(),
    )
    payment = sale.payments.first()
    assert payment.change_amount == Decimal("8.00")


def test_card_payment_has_no_change(stocked_lot, cashier_user):
    sale, _ = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 1}],
        payment={"method": "TARJETA"},
        user=cashier_user,
        client_request_id=uuid4(),
    )
    payment = sale.payments.first()
    assert payment.change_amount == Decimal("0.00")
    assert payment.received_amount is None


def test_insufficient_cash_is_rejected(stocked_lot, cashier_user):
    with pytest.raises(InsufficientPayment):
        create_sale(
            items=[{"product_id": stocked_lot.product_id, "quantity": 1}],
            payment={"method": "EFECTIVO", "received_amount": Decimal("5.00")},
            user=cashier_user,
            client_request_id=uuid4(),
        )
    assert Sale.objects.count() == 0


# ---------------------------------------------------------------------------
# Numeracion
# ---------------------------------------------------------------------------


def test_sale_numbers_are_sequential(stocked_lot, cashier_user):
    first, _ = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 1}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=uuid4(),
    )
    second, _ = create_sale(
        items=[{"product_id": stocked_lot.product_id, "quantity": 1}],
        payment=cash_payment(),
        user=cashier_user,
        client_request_id=uuid4(),
    )
    assert (first.number, second.number) == ("00000001", "00000002")


# ---------------------------------------------------------------------------
# Entradas de mercaderia
# ---------------------------------------------------------------------------


def test_stock_entry_is_idempotent(product, warehouse_user):
    request_id = uuid4()
    items = [
        {
            "product": product,
            "batch_number": "ENT-001",
            "expiry_date": today() + timedelta(days=365),
            "quantity": 10,
            "cost_price": Decimal("8.00"),
        }
    ]

    first, created_first = create_stock_entry(
        supplier="Proveedor Demo",
        received_at=today(),
        items=items,
        user=warehouse_user,
        client_request_id=request_id,
    )
    second, created_second = create_stock_entry(
        supplier="Proveedor Demo",
        received_at=today(),
        items=items,
        user=warehouse_user,
        client_request_id=request_id,
    )

    assert created_first is True
    assert created_second is False
    assert first.pk == second.pk
    assert Lot.objects.get(batch_number="ENT-001").current_quantity == 10


def test_stock_entry_with_different_expiry_for_same_batch_is_rejected(product, warehouse_user):
    expiry = today() + timedelta(days=365)
    create_stock_entry(
        supplier="Proveedor Demo",
        received_at=today(),
        items=[
            {
                "product": product,
                "batch_number": "ENT-002",
                "expiry_date": expiry,
                "quantity": 5,
                "cost_price": Decimal("8.00"),
            }
        ],
        user=warehouse_user,
        client_request_id=uuid4(),
    )

    with pytest.raises(LotExpiryMismatch):
        create_stock_entry(
            supplier="Proveedor Demo",
            received_at=today(),
            items=[
                {
                    "product": product,
                    "batch_number": "ENT-002",
                    "expiry_date": expiry + timedelta(days=30),
                    "quantity": 5,
                    "cost_price": Decimal("8.00"),
                }
            ],
            user=warehouse_user,
            client_request_id=uuid4(),
        )


def test_stock_entry_updates_last_cost(product, warehouse_user):
    create_stock_entry(
        supplier="Proveedor Demo",
        received_at=today(),
        items=[
            {
                "product": product,
                "batch_number": "ENT-003",
                "expiry_date": today() + timedelta(days=365),
                "quantity": 5,
                "cost_price": Decimal("9.75"),
            }
        ],
        user=warehouse_user,
        client_request_id=uuid4(),
    )
    product.refresh_from_db()
    assert product.last_cost == Decimal("9.7500")


# ---------------------------------------------------------------------------
# Ajustes y fraccionamiento
# ---------------------------------------------------------------------------


def test_adjustment_requires_a_reason(stocked_lot, admin_user):
    with pytest.raises(ValidationError):
        adjust_stock(lot_id=stocked_lot.pk, quantity_delta=-1, reason="   ", user=admin_user)


def test_adjustment_records_movement_and_user(stocked_lot, admin_user):
    movement = adjust_stock(
        lot_id=stocked_lot.pk,
        quantity_delta=-2,
        reason="Averia en estante",
        user=admin_user,
    )
    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 8
    assert movement.quantity_delta == -2
    assert movement.created_by == admin_user
    assert movement.balance_after == 8


def test_fractionation_moves_stock_between_presentations(product, warehouse_user):
    from apps.catalog.models import PresentationType, Product, UnitConversion

    blister = Product.objects.create(
        group=product.group,
        presentation=PresentationType.BLISTER,
        presentation_detail="x 10",
        barcode="7000000000002",
        sale_price=Decimal("1.80"),
    )
    UnitConversion.objects.create(group=product.group, source=product, target=blister, factor=10)

    box_lot = Lot.objects.create(
        product=product,
        batch_number="CAJA-01",
        expiry_date=today() + timedelta(days=200),
        current_quantity=5,
        cost_price=Decimal("8.00"),
    )

    out_movement, in_movement = fractionate(
        source_lot_id=box_lot.pk,
        quantity=2,
        batch_number="BLI-01",
        expiry_date=today() + timedelta(days=200),
        user=warehouse_user,
    )

    box_lot.refresh_from_db()
    blister_lot = Lot.objects.get(batch_number="BLI-01")
    assert box_lot.current_quantity == 3
    assert blister_lot.current_quantity == 20
    assert out_movement.quantity_delta == -2
    assert in_movement.quantity_delta == 20
    # El costo se prorratea por el factor de conversion.
    assert blister_lot.cost_price == Decimal("0.8000")

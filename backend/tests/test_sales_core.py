"""Pruebas del nucleo: FEFO, vencimientos, stock y atomicidad."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.audit.models import AuditAction, AuditEvent
from apps.catalog.models import PresentationType
from apps.inventory.exceptions import (
    InsufficientStock,
    InvalidConversion,
    LotBlocked,
    LotExpired,
    LotExpiryMismatch,
)
from apps.inventory.models import Lot, MovementType, StockMovement
from apps.inventory.services import (
    adjust_stock,
    block_lot,
    create_stock_entry,
    fractionate,
    is_expired,
    sellable_lots,
    today,
)
from apps.sales.exceptions import InsufficientPayment
from apps.sales.models import Sale, SaleItemLot
from apps.sales.services import create_sale
from tests.base import BaseTestCase
from tests.factories import ProductFactory, UnitConversionFactory


def cash_payment(amount="100.00"):
    return {"method": "EFECTIVO", "received_amount": Decimal(amount)}


class ExpiryTests(BaseTestCase):
    """Q2: un lote vence al final de su fecha."""

    def test_lot_expiring_today_is_still_sellable(self):
        lot = self.make_lot(days_to_expiry=0, quantity=5)

        self.assertIs(is_expired(lot), False)
        self.assertEqual(list(sellable_lots(lot.product)), [lot])

    def test_lot_expired_yesterday_is_not_sellable(self):
        lot = self.make_lot(days_to_expiry=-1, quantity=5)

        self.assertIs(is_expired(lot), True)
        self.assertEqual(list(sellable_lots(lot.product)), [])

    def test_blocked_lot_is_not_sellable(self):
        lot = self.make_lot(days_to_expiry=30, quantity=5)
        lot.is_blocked = True
        lot.save(update_fields=["is_blocked"])

        self.assertEqual(list(sellable_lots(lot.product)), [])

    def test_expired_lot_cannot_be_sold(self):
        lot = self.make_lot(days_to_expiry=-1, quantity=5)

        with self.assertRaises(InsufficientStock):
            create_sale(
                items=[{"product_id": lot.product_id, "quantity": 1}],
                payment=cash_payment(),
                user=self.cashier_user,
                client_request_id=uuid4(),
            )
        self.assertEqual(lot.current_quantity, 5)


class FefoTests(BaseTestCase):
    def test_fefo_consumes_the_soonest_expiring_lot_first(self):
        later = self.make_lot(days_to_expiry=200, quantity=10, batch="TARDE")
        sooner = self.make_lot(days_to_expiry=30, quantity=10, batch="PRONTO")

        sale, _ = create_sale(
            items=[{"product_id": sooner.product_id, "quantity": 6}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        sooner.refresh_from_db()
        later.refresh_from_db()
        self.assertEqual(sooner.current_quantity, 4)
        self.assertEqual(later.current_quantity, 10)

        allocation = SaleItemLot.objects.get(sale_item__sale=sale)
        self.assertEqual(allocation.lot_id, sooner.pk)
        self.assertEqual(allocation.quantity, 6)

    def test_fefo_spans_multiple_lots_when_needed(self):
        sooner = self.make_lot(days_to_expiry=10, quantity=3, batch="A")
        later = self.make_lot(days_to_expiry=100, quantity=10, batch="B")

        sale, _ = create_sale(
            items=[{"product_id": sooner.product_id, "quantity": 5}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        sooner.refresh_from_db()
        later.refresh_from_db()
        self.assertEqual(sooner.current_quantity, 0)
        self.assertEqual(later.current_quantity, 8)

        allocations = SaleItemLot.objects.filter(sale_item__sale=sale).order_by("lot__expiry_date")
        self.assertEqual(
            [(a.lot_id, a.quantity) for a in allocations], [(sooner.pk, 3), (later.pk, 2)]
        )

    def test_duplicate_product_lines_are_consolidated(self):
        lot = self.make_lot(quantity=10)

        sale, _ = create_sale(
            items=[
                {"product_id": lot.product_id, "quantity": 2},
                {"product_id": lot.product_id, "quantity": 3},
            ],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        self.assertEqual(sale.items.count(), 1)
        self.assertEqual(sale.items.first().quantity, 5)
        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 5)


class StockIntegrityTests(BaseTestCase):
    def test_sale_rejects_more_than_available_and_writes_nothing(self):
        lot = self.make_lot(days_to_expiry=50, quantity=3)

        with self.assertRaises(InsufficientStock) as ctx:
            create_sale(
                items=[{"product_id": lot.product_id, "quantity": 4}],
                payment=cash_payment(),
                user=self.cashier_user,
                client_request_id=uuid4(),
            )

        self.assertEqual(ctx.exception.business_details["available"], 3)
        self.assertEqual(ctx.exception.business_details["requested"], 4)
        self.assertEqual(Sale.objects.count(), 0)
        # El unico movimiento es la carga inicial del fixture: no se genero
        # ningun movimiento de venta ni descuento parcial.
        self.assertEqual(StockMovement.objects.filter(movement_type=MovementType.SALE).count(), 0)
        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 3)

    def test_stock_never_goes_negative_at_the_database_level(self):
        lot = self.make_lot()

        lot.current_quantity = -1
        with self.assertRaises(IntegrityError):
            lot.save()

    def test_movements_are_immutable(self):
        lot = self.make_lot()
        movement = StockMovement.objects.create(
            lot=lot,
            product=lot.product,
            movement_type=MovementType.ADJUSTMENT_IN,
            quantity_delta=1,
            balance_after=11,
            created_by=self.cashier_user,
        )

        movement.quantity_delta = 5
        with self.assertRaises(ValidationError):
            movement.save()

        with self.assertRaises(ValidationError):
            movement.delete()


class IdempotencyTests(BaseTestCase):
    def test_same_client_request_id_does_not_duplicate_the_sale(self):
        lot = self.make_lot(quantity=10)
        request_id = uuid4()

        first, created_first = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 2}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=request_id,
        )
        second, created_second = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 2}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=request_id,
        )

        self.assertIs(created_first, True)
        self.assertIs(created_second, False)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Sale.objects.count(), 1)
        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 8)


class FrozenPriceTests(BaseTestCase):
    def test_price_is_frozen_in_the_sale_line(self):
        lot = self.make_lot()
        sale, _ = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 1}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        product = lot.product
        product.sale_price = Decimal("99.00")
        product.save(update_fields=["sale_price"])

        item = sale.items.first()
        item.refresh_from_db()
        self.assertEqual(item.unit_price, Decimal("12.00"))
        self.assertEqual(sale.total, Decimal("12.00"))

    def test_total_uses_decimal_arithmetic(self):
        lot = self.make_lot()

        sale, _ = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 3}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        self.assertEqual(sale.total, Decimal("36.00"))


class PaymentTests(BaseTestCase):
    def test_cash_payment_returns_change(self):
        lot = self.make_lot()

        sale, _ = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 1}],
            payment={"method": "EFECTIVO", "received_amount": Decimal("20.00")},
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        self.assertEqual(sale.payments.first().change_amount, Decimal("8.00"))

    def test_card_payment_has_no_change(self):
        lot = self.make_lot()

        sale, _ = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 1}],
            payment={"method": "TARJETA"},
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        payment = sale.payments.first()
        self.assertEqual(payment.change_amount, Decimal("0.00"))
        self.assertIsNone(payment.received_amount)

    def test_insufficient_cash_is_rejected(self):
        lot = self.make_lot()

        with self.assertRaises(InsufficientPayment):
            create_sale(
                items=[{"product_id": lot.product_id, "quantity": 1}],
                payment={"method": "EFECTIVO", "received_amount": Decimal("5.00")},
                user=self.cashier_user,
                client_request_id=uuid4(),
            )

        self.assertEqual(Sale.objects.count(), 0)


class SaleNumberTests(BaseTestCase):
    def test_sale_numbers_are_sequential(self):
        lot = self.make_lot(quantity=10)

        first, _ = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 1}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=uuid4(),
        )
        second, _ = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 1}],
            payment=cash_payment(),
            user=self.cashier_user,
            client_request_id=uuid4(),
        )

        self.assertEqual((first.number, second.number), ("00000001", "00000002"))


class StockEntryTests(BaseTestCase):
    def test_stock_entry_is_idempotent(self):
        request_id = uuid4()
        items = [
            {
                "product": self.product,
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
            user=self.warehouse_user,
            client_request_id=request_id,
        )
        second, created_second = create_stock_entry(
            supplier="Proveedor Demo",
            received_at=today(),
            items=items,
            user=self.warehouse_user,
            client_request_id=request_id,
        )

        self.assertIs(created_first, True)
        self.assertIs(created_second, False)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Lot.objects.get(batch_number="ENT-001").current_quantity, 10)

    def test_stock_entry_with_different_expiry_for_same_batch_is_rejected(self):
        expiry = today() + timedelta(days=365)
        create_stock_entry(
            supplier="Proveedor Demo",
            received_at=today(),
            items=[
                {
                    "product": self.product,
                    "batch_number": "ENT-002",
                    "expiry_date": expiry,
                    "quantity": 5,
                    "cost_price": Decimal("8.00"),
                }
            ],
            user=self.warehouse_user,
            client_request_id=uuid4(),
        )

        with self.assertRaises(LotExpiryMismatch):
            create_stock_entry(
                supplier="Proveedor Demo",
                received_at=today(),
                items=[
                    {
                        "product": self.product,
                        "batch_number": "ENT-002",
                        "expiry_date": expiry + timedelta(days=30),
                        "quantity": 5,
                        "cost_price": Decimal("8.00"),
                    }
                ],
                user=self.warehouse_user,
                client_request_id=uuid4(),
            )

    def test_stock_entry_updates_last_cost(self):
        create_stock_entry(
            supplier="Proveedor Demo",
            received_at=today(),
            items=[
                {
                    "product": self.product,
                    "batch_number": "ENT-003",
                    "expiry_date": today() + timedelta(days=365),
                    "quantity": 5,
                    "cost_price": Decimal("9.75"),
                }
            ],
            user=self.warehouse_user,
            client_request_id=uuid4(),
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.last_cost, Decimal("9.7500"))


class AdjustmentTests(BaseTestCase):
    def test_adjustment_requires_a_reason(self):
        lot = self.make_lot()

        with self.assertRaises(ValidationError):
            adjust_stock(
                lot_id=lot.pk,
                quantity_delta=-1,
                reason="   ",
                user=self.admin_user,
            )

    def test_adjustment_records_movement_and_user(self):
        lot = self.make_lot()

        movement = adjust_stock(
            lot_id=lot.pk,
            quantity_delta=-2,
            reason="Averia en estante",
            user=self.admin_user,
        )

        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 8)
        self.assertEqual(movement.quantity_delta, -2)
        self.assertEqual(movement.created_by, self.admin_user)
        self.assertEqual(movement.balance_after, 8)


class FractionationTests(BaseTestCase):
    """Reglas RF1-RF7 definidas en apps/inventory/services.py."""

    def add_blister(self, *, factor=10, is_active=True):
        """Presentacion menor del grupo con su conversion caja -> blister."""
        blister = ProductFactory(
            group=self.product.group,
            presentation=PresentationType.BLISTER,
            presentation_detail=f"x {factor}",
            sale_price=Decimal("1.80"),
            is_active=is_active,
        )
        UnitConversionFactory(
            group=self.product.group,
            source=self.product,
            target=blister,
            factor=factor,
        )
        return blister

    def test_fractionation_moves_stock_between_presentations(self):
        blister = self.add_blister(factor=10)
        box_lot = self.make_lot(days_to_expiry=200, quantity=5, cost="8.0000", batch="CAJA-01")

        out_movement, in_movement = fractionate(
            source_lot_id=box_lot.pk,
            quantity=2,
            user=self.warehouse_user,
        )

        box_lot.refresh_from_db()
        blister_lot = Lot.objects.get(product=blister, batch_number="CAJA-01")
        self.assertEqual(box_lot.current_quantity, 3)
        self.assertEqual(blister_lot.current_quantity, 20)
        # RF4: el destino hereda el lote y el vencimiento del origen.
        self.assertEqual(blister_lot.batch_number, box_lot.batch_number)
        self.assertEqual(blister_lot.expiry_date, box_lot.expiry_date)
        self.assertEqual(out_movement.quantity_delta, -2)
        self.assertEqual(in_movement.quantity_delta, 20)
        self.assertEqual(out_movement.movement_type, MovementType.FRACTIONATION_OUT)
        self.assertEqual(in_movement.movement_type, MovementType.FRACTIONATION_IN)
        # RF6: el costo del destino es el del origen dividido por el factor.
        self.assertEqual(blister_lot.cost_price, Decimal("0.8000"))

    def test_fractionation_reuses_the_target_lot(self):
        blister = self.add_blister(factor=10)
        box_lot = self.make_lot(days_to_expiry=200, quantity=5, cost="8.0000", batch="CAJA-01")

        fractionate(source_lot_id=box_lot.pk, quantity=1, user=self.warehouse_user)
        fractionate(source_lot_id=box_lot.pk, quantity=1, user=self.warehouse_user)

        # RF5: se suma al mismo lote destino; no se crea un duplicado.
        self.assertEqual(Lot.objects.filter(product=blister).count(), 1)
        self.assertEqual(Lot.objects.get(product=blister).current_quantity, 20)

    def test_fractionation_rejects_an_expired_source(self):
        self.add_blister(factor=10)
        expired = self.make_lot(days_to_expiry=-1, quantity=5, batch="VENCIDO")

        with self.assertRaises(LotExpired):
            fractionate(source_lot_id=expired.pk, quantity=1, user=self.warehouse_user)

    def test_fractionation_rejects_a_blocked_source(self):
        self.add_blister(factor=10)
        lot = self.make_lot(days_to_expiry=200, quantity=5, batch="BLOQUEADO")
        block_lot(lot_id=lot.pk, reason="Cuarentena", user=self.warehouse_user)

        with self.assertRaises(LotBlocked):
            fractionate(source_lot_id=lot.pk, quantity=1, user=self.warehouse_user)

    def test_fractionation_rejects_more_than_available(self):
        self.add_blister(factor=10)
        lot = self.make_lot(days_to_expiry=200, quantity=5, batch="CAJA-01")

        with self.assertRaises(InsufficientStock):
            fractionate(source_lot_id=lot.pk, quantity=6, user=self.warehouse_user)

    def test_fractionation_requires_a_conversion(self):
        lot = self.make_lot(days_to_expiry=200, quantity=5, batch="CAJA-01")

        with self.assertRaises(InvalidConversion):
            fractionate(source_lot_id=lot.pk, quantity=1, user=self.warehouse_user)

    def test_fractionation_rejects_an_inactive_target(self):
        self.add_blister(factor=10, is_active=False)
        lot = self.make_lot(days_to_expiry=200, quantity=5, batch="CAJA-01")

        with self.assertRaises(InvalidConversion):
            fractionate(source_lot_id=lot.pk, quantity=1, user=self.warehouse_user)

    def test_fractionation_rejects_a_non_positive_quantity(self):
        self.add_blister(factor=10)
        lot = self.make_lot(days_to_expiry=200, quantity=5, batch="CAJA-01")

        with self.assertRaises(ValidationError):
            fractionate(source_lot_id=lot.pk, quantity=0, user=self.warehouse_user)

    def test_fractionation_records_an_audit_event(self):
        self.add_blister(factor=10)
        lot = self.make_lot(days_to_expiry=200, quantity=5, batch="CAJA-01")

        fractionate(source_lot_id=lot.pk, quantity=1, user=self.warehouse_user)

        event = AuditEvent.objects.get(action=AuditAction.FRACTIONATION)
        self.assertEqual(event.actor, self.warehouse_user)

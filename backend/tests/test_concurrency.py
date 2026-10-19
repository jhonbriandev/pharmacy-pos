"""Pruebas de concurrencia: el riesgo mas grave del proyecto (R1).

Requieren PostgreSQL real y ``TransactionTestCase``: con SQLite, o dentro de la
transaccion de un ``TestCase``, no se reproduciria una condicion de carrera de
verdad.

Si estas pruebas fallan, **no se despliega**. Vender dos veces el mismo ultimo
item es un error de dinero y de inventario, no un detalle cosmetico.
"""

import threading
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import connections
from django.test import TransactionTestCase

from apps.accounts.models import Role
from apps.inventory.exceptions import InsufficientStock
from apps.inventory.services import find_consistency_issues, today
from apps.sales.models import Sale
from apps.sales.services import create_sale
from tests.factories import LotFactory, ProductFactory, UserFactory


def _sell(lot, user, results, errors, barrier):
    """Intenta vender una unidad en un hilo con su propia conexion."""
    try:
        barrier.wait(timeout=10)
        sale, _ = create_sale(
            items=[{"product_id": lot.product_id, "quantity": 1}],
            payment={"method": "EFECTIVO", "received_amount": Decimal("50.00")},
            user=user,
            client_request_id=uuid4(),
        )
        results.append(sale.number)
    except InsufficientStock as exc:
        errors.append(exc)
    except Exception as exc:  # pragma: no cover - se reporta para diagnostico
        errors.append(exc)
    finally:
        # Cada hilo abre su propia conexion: hay que cerrarla al terminar.
        connections.close_all()


class ConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.cashier_user = UserFactory(role=Role.CAJERO)
        self.product = ProductFactory()

    def make_lot(self, *, quantity, batch, days_to_expiry=90):
        return LotFactory(
            product=self.product,
            batch_number=batch,
            expiry_date=today() + timedelta(days=days_to_expiry),
            stock=quantity,
        )

    def run_concurrently(self, lot, threads_count):
        barrier = threading.Barrier(threads_count)
        results = []
        errors = []
        threads = [
            threading.Thread(
                target=_sell,
                args=(lot, self.cashier_user, results, errors, barrier),
            )
            for _ in range(threads_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        return results, errors

    def test_two_concurrent_sales_of_the_last_unit(self):
        """Dos cajeros venden el ultimo item: solo uno gana, el stock queda en 0."""
        lot = self.make_lot(quantity=1, batch="CONC-UNO")

        results, errors = self.run_concurrently(lot, 2)

        lot.refresh_from_db()

        self.assertEqual(
            len(results), 1, f"Debe confirmarse exactamente una venta; hubo {len(results)}"
        )
        self.assertEqual(
            len(errors), 1, f"Debe fallar exactamente una venta; fallaron {len(errors)}"
        )
        self.assertIsInstance(errors[0], InsufficientStock)
        self.assertEqual(lot.current_quantity, 0, "El stock nunca puede quedar negativo")
        self.assertEqual(Sale.objects.count(), 1)

    def test_many_concurrent_sales_never_oversell(self):
        """10 intentos simultaneos sobre 4 unidades: se venden exactamente 4."""
        lot = self.make_lot(quantity=4, batch="CONC-01")

        results, errors = self.run_concurrently(lot, 10)

        lot.refresh_from_db()

        self.assertEqual(len(results), 4)
        self.assertEqual(len(errors), 6)
        self.assertEqual(lot.current_quantity, 0)
        self.assertEqual(Sale.objects.count(), 4)
        # Todos los errores deben ser de stock, no fallos inesperados.
        self.assertTrue(all(isinstance(error, InsufficientStock) for error in errors))

    def test_concurrent_sales_get_distinct_numbers(self):
        """Los numeros de venta no se repiten ni se pisan bajo concurrencia."""
        lot = self.make_lot(quantity=10, batch="CONC-02")

        results, errors = self.run_concurrently(lot, 5)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 5)
        self.assertEqual(len(set(results)), 5, f"Numeros repetidos: {results}")
        self.assertEqual(sorted(results), [f"{n:08d}" for n in range(1, 6)])

    def test_consistency_after_concurrent_sales(self):
        """Tras la carrera, la cache del lote coincide con su libro mayor."""
        lot = self.make_lot(quantity=3, batch="CONC-03")

        self.run_concurrently(lot, 5)

        self.assertEqual(find_consistency_issues(), [])

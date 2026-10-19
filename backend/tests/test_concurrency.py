"""Pruebas de concurrencia: el riesgo mas grave del proyecto (R1).

Requieren PostgreSQL real y ``transaction=True``: con SQLite o con el modo
transaccional de pytest no se reproduciria una condicion de carrera de verdad.

Si estas pruebas fallan, **no se despliega**. Vender dos veces el mismo ultimo
item es un error de dinero y de inventario, no un detalle cosmetico.
"""

import threading
from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import connections

from apps.inventory.exceptions import InsufficientStock
from apps.sales.models import Sale
from apps.sales.services import create_sale

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.concurrency]


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


def test_two_concurrent_sales_of_the_last_unit(stocked_lot, cashier_user):
    """Dos cajeros venden el ultimo item: solo uno gana, el stock queda en 0."""
    stocked_lot.current_quantity = 1
    stocked_lot.save(update_fields=["current_quantity"])

    barrier = threading.Barrier(2)
    results: list[str] = []
    errors: list[Exception] = []

    threads = [
        threading.Thread(target=_sell, args=(stocked_lot, cashier_user, results, errors, barrier))
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    stocked_lot.refresh_from_db()

    assert len(results) == 1, f"Debe confirmarse exactamente una venta; hubo {len(results)}"
    assert len(errors) == 1, f"Debe fallar exactamente una venta; fallaron {len(errors)}"
    assert isinstance(errors[0], InsufficientStock)
    assert stocked_lot.current_quantity == 0, "El stock nunca puede quedar negativo"
    assert Sale.objects.count() == 1


def test_many_concurrent_sales_never_oversell(lot_factory, cashier_user):
    """10 intentos simultaneos sobre 4 unidades: se venden exactamente 4."""
    lot = lot_factory(days_to_expiry=90, quantity=4, batch="CONC-01")

    barrier = threading.Barrier(10)
    results: list[str] = []
    errors: list[Exception] = []

    threads = [
        threading.Thread(target=_sell, args=(lot, cashier_user, results, errors, barrier))
        for _ in range(10)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    lot.refresh_from_db()

    assert len(results) == 4
    assert len(errors) == 6
    assert lot.current_quantity == 0
    assert Sale.objects.count() == 4
    # Todos los errores deben ser de stock, no fallos inesperados.
    assert all(isinstance(error, InsufficientStock) for error in errors)


def test_concurrent_sales_get_distinct_numbers(lot_factory, cashier_user):
    """Los numeros de venta no se repiten ni se pisan bajo concurrencia."""
    lot = lot_factory(days_to_expiry=90, quantity=10, batch="CONC-02")

    barrier = threading.Barrier(5)
    results: list[str] = []
    errors: list[Exception] = []

    threads = [
        threading.Thread(target=_sell, args=(lot, cashier_user, results, errors, barrier))
        for _ in range(5)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    assert len(results) == 5
    assert len(set(results)) == 5, f"Numeros repetidos: {results}"
    assert sorted(results) == [f"{n:08d}" for n in range(1, 6)]


def test_consistency_after_concurrent_sales(lot_factory, cashier_user):
    """Tras la carrera, la cache del lote coincide con su libro mayor."""
    from apps.inventory.services import find_consistency_issues

    lot = lot_factory(days_to_expiry=90, quantity=3, batch="CONC-03")

    barrier = threading.Barrier(5)
    results: list[str] = []
    errors: list[Exception] = []

    threads = [
        threading.Thread(target=_sell, args=(lot, cashier_user, results, errors, barrier))
        for _ in range(5)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert find_consistency_issues() == []

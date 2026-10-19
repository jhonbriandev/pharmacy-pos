"""Configuracion compartida de las pruebas.

Los fixtures crean datos **ficticios**. Nunca se usan datos reales.
"""

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.accounts.models import Role, User
from apps.catalog.models import PresentationType, Product, ProductGroup
from apps.inventory.models import Lot, MovementType
from apps.inventory.services import apply_movement, today

DEFAULT_PASSWORD = "PruebaSegura123"


def make_user(username: str, role: str, **kwargs) -> User:
    user = User(username=username, role=role, first_name="Prueba", last_name=role.title(), **kwargs)
    user.set_password(DEFAULT_PASSWORD)
    user.save()
    return user


@pytest.fixture
def admin_user(db):
    return make_user("90000001", Role.ADMIN)


@pytest.fixture
def regent_user(db):
    return make_user("90000002", Role.REGENTE)


@pytest.fixture
def cashier_user(db):
    return make_user("90000003", Role.CAJERO)


@pytest.fixture
def other_cashier(db):
    return make_user("90000004", Role.CAJERO)


@pytest.fixture
def warehouse_user(db):
    return make_user("90000005", Role.ALMACEN)


@pytest.fixture
def auditor_user(db):
    return make_user("90000006", Role.AUDITOR)


@pytest.fixture
def product(db) -> Product:
    """Producto simple: caja de 100 tabletas a S/ 12.00."""
    group = ProductGroup.objects.create(
        name="Paracetamol",
        concentration="500 mg",
        pharmaceutical_form="TABLETA",
    )
    return Product.objects.create(
        group=group,
        presentation=PresentationType.BOX,
        presentation_detail="x 100",
        barcode="7000000000001",
        sale_price=Decimal("12.00"),
        min_stock=5,
    )


@pytest.fixture
def lot_factory(db, product):
    """Crea lotes con vencimiento relativo a hoy.

    El stock inicial se carga **mediante un movimiento**, igual que en
    produccion: si se creara con ``current_quantity`` directo, el libro mayor y
    la cache no cuadrarian y la verificacion de consistencia lo detectaria.
    """

    def _create(*, days_to_expiry: int = 100, quantity: int = 10, cost="8.0000", batch=None):
        lot = Lot.objects.create(
            product=product,
            batch_number=batch or f"LOTE-{days_to_expiry}-{quantity}",
            expiry_date=today() + timedelta(days=days_to_expiry),
            current_quantity=0,
            cost_price=Decimal(cost),
        )
        if quantity:
            apply_movement(
                lot=lot,
                movement_type=MovementType.ENTRY,
                quantity_delta=quantity,
                reason="Carga inicial de prueba",
            )
        return lot

    return _create


@pytest.fixture
def stocked_lot(lot_factory):
    """Lote con 10 unidades que vence en 100 dias."""
    return lot_factory(days_to_expiry=100, quantity=10)


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()

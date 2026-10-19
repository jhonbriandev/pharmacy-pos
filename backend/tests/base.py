"""Base comun de las pruebas: usuarios por rol y helpers de datos."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Role
from apps.inventory.services import today
from tests.factories import LotFactory, ProductFactory, UserFactory


class UsersMixin:
    """Un usuario por rol, creado una sola vez por clase de prueba."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin_user = UserFactory(role=Role.ADMIN)
        cls.regent_user = UserFactory(role=Role.REGENTE)
        cls.cashier_user = UserFactory(role=Role.CAJERO)
        cls.other_cashier = UserFactory(role=Role.CAJERO)
        cls.warehouse_user = UserFactory(role=Role.ALMACEN)
        cls.auditor_user = UserFactory(role=Role.AUDITOR)

    def setUp(self):
        super().setUp()
        # Un producto nuevo por prueba: evita heredar lotes, precios o bloqueos
        # de otra prueba.
        self.product = ProductFactory()

    def make_lot(
        self,
        *,
        product=None,
        days_to_expiry=100,
        quantity=10,
        cost="8.0000",
        batch=None,
    ):
        """Lote con stock cargado mediante un movimiento de entrada."""
        data = {
            "product": product or self.product,
            "expiry_date": today() + timedelta(days=days_to_expiry),
            "cost_price": Decimal(cost),
            "stock": quantity,
        }
        if batch is not None:
            data["batch_number"] = batch
        return LotFactory(**data)


class BaseTestCase(UsersMixin, TestCase):
    """Pruebas de servicios y modelos (sin cliente HTTP)."""


class BaseAPITestCase(UsersMixin, APITestCase):
    """Pruebas de API: un cliente autenticado por rol."""

    def api_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

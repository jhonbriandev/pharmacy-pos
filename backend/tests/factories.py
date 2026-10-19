"""Factories de datos ficticios para las pruebas.

Nunca se usan datos reales de personas: los DNI, nombres y lotes son inventados
por la propia suite.
"""

from datetime import timedelta
from decimal import Decimal

import factory

from apps.accounts.models import Role, User
from apps.catalog.models import PresentationType, Product, ProductGroup, UnitConversion
from apps.inventory.models import Lot, MovementType
from apps.inventory.services import apply_movement, today

PASSWORD = "PruebaSegura123"


class UserFactory(factory.django.DjangoModelFactory):
    """Usuario activo con DNI de 8 digitos y contrasena conocida."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"9{n:07d}")
    first_name = "Prueba"
    last_name = "Usuario"
    role = Role.CAJERO
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or PASSWORD)
        if create:
            self.save(update_fields=["password"])


class ProductGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductGroup

    name = "Paracetamol"
    concentration = "500 mg"
    pharmaceutical_form = "TABLETA"


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    group = factory.SubFactory(ProductGroupFactory)
    presentation = PresentationType.BOX
    presentation_detail = "x 100"
    barcode = factory.Sequence(lambda n: f"7000000{n:06d}")
    unit_label = "tableta"
    sale_price = Decimal("12.00")
    min_stock = 5


class UnitConversionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UnitConversion

    group = factory.SelfAttribute("source.group")
    source = factory.SubFactory(ProductFactory)
    target = factory.SubFactory(ProductFactory)
    factor = 10


class LotFactory(factory.django.DjangoModelFactory):
    """Lote con stock cargado por el libro mayor, no escribiendo la cache."""

    class Meta:
        model = Lot
        skip_postgeneration_save = True

    product = factory.SubFactory(ProductFactory)
    batch_number = factory.Sequence(lambda n: f"LOTE-{n:05d}")
    expiry_date = factory.LazyFunction(lambda: today() + timedelta(days=100))
    cost_price = Decimal("8.0000")
    current_quantity = 0

    @factory.post_generation
    def stock(self, create, extracted, **kwargs):
        if not create:
            return
        quantity = 10 if extracted is None else extracted
        if quantity:
            apply_movement(
                lot=self,
                movement_type=MovementType.ENTRY,
                quantity_delta=quantity,
                reason="Carga inicial de prueba",
            )

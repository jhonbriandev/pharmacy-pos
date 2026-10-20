"""Comando de datos ficticios para desarrollo y demostracion.

Crea usuarios de todos los roles, un catalogo de farmacia con presentaciones
(caja, blister, unidad), lotes con vencimientos variados y algunas ventas.

**Los datos son ficticios.** Esta prohibido usar datos reales de clientes o
pacientes en desarrollo y pruebas.

Es idempotente: ejecutarlo dos veces no duplica nada.
"""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Role, User
from apps.catalog.models import (
    ActiveIngredient,
    Category,
    Laboratory,
    PresentationType,
    Product,
    ProductGroup,
    UnitConversion,
)
from apps.inventory.services import create_stock_entry, today
from apps.sales.services import create_sale

PASSWORD = "Farmacia2026"  # noqa: S105 - contrasena de demostracion, solo local

USERS = [
    ("10000001", "Ana", "Torres Rios", Role.ADMIN),
    ("10000002", "Luis", "Paredes Vega", Role.REGENTE),
    ("10000003", "Rosa", "Quispe Lima", Role.CAJERO),
    ("10000004", "Jorge", "Salazar Nunez", Role.CAJERO),
    ("10000005", "Milagros", "Cordova Paz", Role.ALMACEN),
    ("10000006", "Carlos", "Mendoza Ruiz", Role.AUDITOR),
]


class Command(BaseCommand):
    help = "Carga datos ficticios de demostracion (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-sales",
            action="store_true",
            help="No generar ventas de ejemplo.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Permite ejecutarlo con DEBUG=False (entorno de demostracion).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "`seed` carga datos ficticios y solo debe ejecutarse en desarrollo. "
                "En produccion crea la cuenta con `create_admin`. "
                "Si es un entorno de demostracion, repite con --force."
            )

        self.stdout.write(self.style.MIGRATE_HEADING("Cargando datos de demostracion"))
        users = self._create_users()
        catalog = self._create_catalog()
        self._create_stock(catalog, users["almacen"])
        if not options["no_sales"]:
            self._create_sales(catalog, users["cajero"])

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos de demostracion listos."))
        self.stdout.write("")
        self.stdout.write(f"  Usuarios (contrasena: {PASSWORD})")
        for dni, first, last, role in USERS:
            self.stdout.write(f"    {dni}  {first} {last:<18} {Role(role).label}")
        self.stdout.write("")

        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    "  Aviso: entorno con DEBUG=False. Las cuentas recien creadas usan "
                    "una contrasena conocida; desactivalas antes de cargar datos reales "
                    "(no se eliminan: `is_active=False`)."
                )
            )
            self.stdout.write("")

    # ------------------------------------------------------------------
    def _create_users(self) -> dict[str, User]:
        created: dict[str, User] = {}
        reused: list[str] = []
        for dni, first, last, role in USERS:
            user, was_created = User.objects.get_or_create(
                username=dni,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "is_staff": role == Role.ADMIN,
                    "is_superuser": role == Role.ADMIN,
                },
            )
            # La contrasena de demo solo se fija al crear la cuenta. Con
            # `--force` en un entorno con cuentas reales, el seed nunca debe
            # cambiar la contrasena ni el rol de un usuario existente.
            if was_created:
                user.set_password(PASSWORD)
                user.save(update_fields=["password"])
            else:
                reused.append(dni)

            key = {
                Role.ADMIN: "admin",
                Role.REGENTE: "regente",
                Role.CAJERO: "cajero",
                Role.ALMACEN: "almacen",
                Role.AUDITOR: "auditor",
            }[role]
            created.setdefault(key, user)

        if reused:
            self.stdout.write(
                self.style.WARNING("  aviso: ya existian y no se tocaron: " + ", ".join(reused))
            )
        self.stdout.write(f"  usuarios: {User.objects.count()}")
        return created

    # ------------------------------------------------------------------
    def _create_catalog(self) -> dict[str, Product]:
        lab_genfar, _ = Laboratory.objects.get_or_create(name="Genfar")
        lab_bago, _ = Laboratory.objects.get_or_create(name="Bagó")
        lab_medifarma, _ = Laboratory.objects.get_or_create(name="Medifarma")

        cat_analgesico, _ = Category.objects.get_or_create(
            name="Analgesicos", defaults={"description": "Dolor y fiebre"}
        )
        cat_antibiotico, _ = Category.objects.get_or_create(
            name="Antibioticos", defaults={"description": "Infecciones bacterianas"}
        )
        cat_gastro, _ = Category.objects.get_or_create(
            name="Gastrointestinal", defaults={"description": "Digestivo"}
        )

        paracetamol_ing, _ = ActiveIngredient.objects.get_or_create(name="Paracetamol")
        amoxi_ing, _ = ActiveIngredient.objects.get_or_create(name="Amoxicilina")
        omeprazol_ing, _ = ActiveIngredient.objects.get_or_create(name="Omeprazol")
        ibuprofeno_ing, _ = ActiveIngredient.objects.get_or_create(name="Ibuprofeno")

        products: dict[str, Product] = {}

        # --- Paracetamol 500 mg: caja x 100, blister x 10, unidad -----------
        group_para, _ = ProductGroup.objects.get_or_create(
            name="Paracetamol",
            concentration="500 mg",
            pharmaceutical_form="TABLETA",
            laboratory=lab_genfar,
            defaults={"category": cat_analgesico},
        )
        group_para.ingredients.set([paracetamol_ing])

        box_para, _ = Product.objects.get_or_create(
            group=group_para,
            presentation=PresentationType.BOX,
            presentation_detail="x 100",
            defaults={
                "barcode": "7751234500011",
                "unit_label": "tableta",
                "sale_price": Decimal("12.00"),
                "min_stock": 5,
            },
        )
        blister_para, _ = Product.objects.get_or_create(
            group=group_para,
            presentation=PresentationType.BLISTER,
            presentation_detail="x 10",
            defaults={
                "barcode": "7751234500028",
                "unit_label": "tableta",
                "sale_price": Decimal("1.80"),
                "min_stock": 20,
            },
        )
        unit_para, _ = Product.objects.get_or_create(
            group=group_para,
            presentation=PresentationType.UNIT,
            presentation_detail="unidad",
            defaults={
                "barcode": "7751234500035",
                "unit_label": "tableta",
                "sale_price": Decimal("0.20"),
                "min_stock": 50,
            },
        )
        UnitConversion.objects.get_or_create(
            group=group_para, source=box_para, target=blister_para, defaults={"factor": 10}
        )
        UnitConversion.objects.get_or_create(
            group=group_para, source=blister_para, target=unit_para, defaults={"factor": 10}
        )
        products.update(box_para=box_para, blister_para=blister_para, unit_para=unit_para)

        # --- Amoxicilina 500 mg: caja x 60 y blister x 10 -------------------
        group_amoxi, _ = ProductGroup.objects.get_or_create(
            name="Amoxicilina",
            concentration="500 mg",
            pharmaceutical_form="CAPSULA",
            laboratory=lab_bago,
            defaults={"category": cat_antibiotico},
        )
        group_amoxi.ingredients.set([amoxi_ing])
        box_amoxi, _ = Product.objects.get_or_create(
            group=group_amoxi,
            presentation=PresentationType.BOX,
            presentation_detail="x 60",
            defaults={
                "barcode": "7751234500042",
                "unit_label": "capsula",
                "sale_price": Decimal("28.50"),
                "min_stock": 4,
            },
        )
        products["box_amoxi"] = box_amoxi

        # --- Omeprazol 20 mg: caja x 30 -------------------------------------
        group_ome, _ = ProductGroup.objects.get_or_create(
            name="Omeprazol",
            concentration="20 mg",
            pharmaceutical_form="CAPSULA",
            laboratory=lab_medifarma,
            defaults={"category": cat_gastro},
        )
        group_ome.ingredients.set([omeprazol_ing])
        box_ome, _ = Product.objects.get_or_create(
            group=group_ome,
            presentation=PresentationType.BOX,
            presentation_detail="x 30",
            defaults={
                "barcode": "7751234500059",
                "unit_label": "capsula",
                "sale_price": Decimal("15.90"),
                "min_stock": 6,
            },
        )
        products["box_ome"] = box_ome

        # --- Ibuprofeno 400 mg: caja x 100 (producto con stock bajo) --------
        group_ibu, _ = ProductGroup.objects.get_or_create(
            name="Ibuprofeno",
            concentration="400 mg",
            pharmaceutical_form="TABLETA",
            laboratory=lab_genfar,
            defaults={"category": cat_analgesico},
        )
        group_ibu.ingredients.set([ibuprofeno_ing])
        box_ibu, _ = Product.objects.get_or_create(
            group=group_ibu,
            presentation=PresentationType.BOX,
            presentation_detail="x 100",
            defaults={
                "barcode": "7751234500066",
                "unit_label": "tableta",
                "sale_price": Decimal("18.00"),
                "min_stock": 10,
            },
        )
        products["box_ibu"] = box_ibu

        self.stdout.write(f"  productos: {Product.objects.count()}")
        return products

    # ------------------------------------------------------------------
    def _create_stock(self, products: dict[str, Product], user: User) -> None:
        if products["box_para"].lots.exists():
            self.stdout.write("  inventario: ya existia, no se duplica")
            return

        current = today()
        entries = [
            {
                "supplier": "Distribuidora Farmaceutica del Sur",
                "document_number": "F001-00001234",
                "received_at": current - timedelta(days=40),
                "items": [
                    {
                        "product": products["box_para"],
                        "batch_number": "PAR-2401",
                        "expiry_date": current + timedelta(days=400),
                        "quantity": 40,
                        "cost_price": Decimal("8.5000"),
                    },
                    {
                        "product": products["box_amoxi"],
                        "batch_number": "AMO-2401",
                        "expiry_date": current + timedelta(days=300),
                        "quantity": 20,
                        "cost_price": Decimal("19.0000"),
                    },
                    {
                        "product": products["box_ome"],
                        "batch_number": "OME-2401",
                        "expiry_date": current + timedelta(days=200),
                        "quantity": 25,
                        "cost_price": Decimal("10.2000"),
                    },
                ],
            },
            {
                "supplier": "Drogueria Nacional",
                "document_number": "F001-00005678",
                "received_at": current - timedelta(days=10),
                "items": [
                    {
                        "product": products["box_para"],
                        "batch_number": "PAR-2402",
                        "expiry_date": current + timedelta(days=25),
                        "quantity": 15,
                        "cost_price": Decimal("8.8000"),
                    },
                    {
                        "product": products["blister_para"],
                        "batch_number": "PAR-B-2401",
                        "expiry_date": current + timedelta(days=60),
                        "quantity": 30,
                        "cost_price": Decimal("1.2000"),
                    },
                    {
                        "product": products["unit_para"],
                        "batch_number": "PAR-U-2401",
                        "expiry_date": current + timedelta(days=90),
                        "quantity": 200,
                        "cost_price": Decimal("0.1300"),
                    },
                    {
                        "product": products["box_ibu"],
                        "batch_number": "IBU-2401",
                        "expiry_date": current + timedelta(days=120),
                        "quantity": 8,
                        "cost_price": Decimal("12.4000"),
                    },
                ],
            },
        ]

        for entry in entries:
            create_stock_entry(
                supplier=entry["supplier"],
                document_number=entry["document_number"],
                received_at=entry["received_at"],
                items=entry["items"],
                user=user,
                client_request_id=uuid4(),
            )

        # Un lote ya vencido, para demostrar la alerta y el bloqueo de venta.
        create_stock_entry(
            supplier="Drogueria Nacional",
            document_number="F001-00009000",
            received_at=current - timedelta(days=500),
            items=[
                {
                    "product": products["box_ome"],
                    "batch_number": "OME-2301",
                    "expiry_date": current - timedelta(days=5),
                    "quantity": 6,
                    "cost_price": Decimal("9.9000"),
                }
            ],
            user=user,
            client_request_id=uuid4(),
        )

        self.stdout.write("  inventario: 3 entradas registradas")

    # ------------------------------------------------------------------
    def _create_sales(self, products: dict[str, Product], user: User) -> None:
        from apps.sales.models import Sale

        if Sale.objects.exists():
            self.stdout.write("  ventas: ya existian, no se duplican")
            return

        demo_sales = [
            {
                "items": [
                    {"product_id": products["blister_para"].pk, "quantity": 2},
                    {"product_id": products["unit_para"].pk, "quantity": 6},
                ],
                "payment": {"method": "EFECTIVO", "received_amount": Decimal("20.00")},
            },
            {
                "items": [{"product_id": products["box_amoxi"].pk, "quantity": 1}],
                "payment": {"method": "TARJETA"},
            },
            {
                "items": [
                    {"product_id": products["box_para"].pk, "quantity": 1},
                    {"product_id": products["box_ome"].pk, "quantity": 1},
                ],
                "payment": {"method": "TRANSFERENCIA", "reference": "OP-998877"},
            },
        ]

        for demo in demo_sales:
            create_sale(
                items=demo["items"],
                payment=demo["payment"],
                user=user,
                client_request_id=uuid4(),
            )

        self.stdout.write(f"  ventas: {Sale.objects.count()} registradas")

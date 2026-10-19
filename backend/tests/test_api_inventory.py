"""Pruebas de la API de inventario: entradas, ajustes, fraccionamiento y lotes."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from apps.catalog.models import PresentationType
from apps.inventory.models import Lot, StockMovement
from apps.inventory.services import today
from tests.base import BaseAPITestCase
from tests.factories import ProductFactory, UnitConversionFactory


class InventoryApiTests(BaseAPITestCase):
    def entry_payload(self, *, batch="ENT-API-01", quantity=10, days=365, request_id=None):
        return {
            "client_request_id": str(request_id or uuid4()),
            "supplier": "Distribuidora Demo",
            "document_number": "F001-0001",
            "received_at": today().isoformat(),
            "items": [
                {
                    "product": self.product.pk,
                    "batch_number": batch,
                    "expiry_date": (today() + timedelta(days=days)).isoformat(),
                    "quantity": quantity,
                    "cost_price": "8.5000",
                }
            ],
        }

    def test_stock_entry_creates_lot_and_movement(self):
        response = self.api_for(self.warehouse_user).post(
            "/api/v1/stock-entries/", self.entry_payload(), format="json"
        )

        self.assertEqual(response.status_code, 201)
        lot = Lot.objects.get(batch_number="ENT-API-01")
        self.assertEqual(lot.current_quantity, 10)
        self.assertEqual(StockMovement.objects.filter(lot=lot).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.last_cost, Decimal("8.5000"))

    def test_stock_entry_replay_returns_200_and_does_not_duplicate(self):
        client = self.api_for(self.warehouse_user)
        payload = self.entry_payload()

        first = client.post("/api/v1/stock-entries/", payload, format="json")
        second = client.post("/api/v1/stock-entries/", payload, format="json")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.headers["X-Idempotent-Replay"], "true")
        self.assertEqual(Lot.objects.get(batch_number="ENT-API-01").current_quantity, 10)

    def test_stock_entry_rejects_duplicate_batch_lines(self):
        payload = self.entry_payload()
        payload["items"].append(payload["items"][0])

        response = self.api_for(self.warehouse_user).post(
            "/api/v1/stock-entries/", payload, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_cashier_cannot_create_stock_entries(self):
        response = self.api_for(self.cashier_user).post(
            "/api/v1/stock-entries/", self.entry_payload(), format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_adjustment_requires_manager_role(self):
        lot = self.make_lot()
        payload = {"lot": lot.pk, "quantity_delta": -1, "reason": "Averia"}

        self.assertEqual(
            self.api_for(self.warehouse_user)
            .post("/api/v1/stock-adjustments/", payload, format="json")
            .status_code,
            403,
        )

        response = self.api_for(self.regent_user).post(
            "/api/v1/stock-adjustments/", payload, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_adjustment_rejects_unknown_lot(self):
        response = self.api_for(self.admin_user).post(
            "/api/v1/stock-adjustments/",
            {"lot": 999999, "quantity_delta": -1, "reason": "Averia"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_adjustment_cannot_leave_negative_stock(self):
        lot = self.make_lot(quantity=10)

        response = self.api_for(self.admin_user).post(
            "/api/v1/stock-adjustments/",
            {"lot": lot.pk, "quantity_delta": -99, "reason": "Averia"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 10)

    def test_lot_block_prevents_sales(self):
        lot = self.make_lot()

        response = self.api_for(self.regent_user).post(
            f"/api/v1/lots/{lot.pk}/block/",
            {"reason": "Sospecha de falsificacion"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        stock = self.api_for(self.cashier_user).post(
            "/api/v1/sales/",
            {
                "client_request_id": str(uuid4()),
                "items": [{"product_id": lot.product_id, "quantity": 1}],
                "payment": {"method": "EFECTIVO", "received_amount": "20.00"},
            },
            format="json",
        )
        self.assertEqual(stock.status_code, 409)

    def test_expiring_lots_endpoint_excludes_expired(self):
        self.make_lot(days_to_expiry=10, quantity=5, batch="PRONTO")
        self.make_lot(days_to_expiry=400, quantity=5, batch="LEJOS")
        self.make_lot(days_to_expiry=-10, quantity=5, batch="VENCIDO")

        response = self.api_for(self.warehouse_user).get(
            "/api/v1/lots/expiring/", {"within_days": 30}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["batch_number"] for row in response.data], ["PRONTO"])

    def test_expired_lots_endpoint_lists_only_expired(self):
        self.make_lot(days_to_expiry=10, quantity=5, batch="PRONTO")
        self.make_lot(days_to_expiry=-10, quantity=5, batch="VENCIDO")

        response = self.api_for(self.warehouse_user).get("/api/v1/lots/expired/")
        self.assertEqual([row["batch_number"] for row in response.data], ["VENCIDO"])

    def test_fractionation_endpoint_splits_a_box(self):
        blister = ProductFactory(
            group=self.product.group,
            presentation=PresentationType.BLISTER,
            presentation_detail="x 10",
            sale_price=Decimal("1.80"),
        )
        UnitConversionFactory(
            group=self.product.group,
            source=self.product,
            target=blister,
            factor=10,
        )

        created = self.api_for(self.warehouse_user).post(
            "/api/v1/stock-entries/",
            self.entry_payload(batch="CAJA-FRAC", quantity=4),
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        box_lot = Lot.objects.get(batch_number="CAJA-FRAC")

        response = self.api_for(self.warehouse_user).post(
            "/api/v1/stock-fractionations/",
            {"source_lot": box_lot.pk, "quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        box_lot.refresh_from_db()
        self.assertEqual(box_lot.current_quantity, 3)
        # RF4: el lote destino conserva el numero de lote del origen.
        blister_lot = Lot.objects.get(product=blister, batch_number="CAJA-FRAC")
        self.assertEqual(blister_lot.current_quantity, 10)

    def test_consistency_endpoint_reports_ok(self):
        self.make_lot()

        response = self.api_for(self.admin_user).get("/api/v1/inventory/consistency/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"consistent": True, "issues_count": 0, "issues": []})

    def test_low_stock_endpoint_flags_products_below_minimum(self):
        # self.product tiene min_stock=5 y ningun lote: debe aparecer.
        response = self.api_for(self.warehouse_user).get("/api/v1/products/low-stock/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [self.product.pk])
        self.assertEqual(response.data[0]["stock"], 0)

    def test_stock_movements_are_read_only(self):
        self.make_lot()
        client = self.api_for(self.warehouse_user)
        self.assertEqual(client.get("/api/v1/stock-movements/").status_code, 200)
        self.assertEqual(
            client.post("/api/v1/stock-movements/", {}, format="json").status_code, 405
        )

    def test_auditor_can_read_movements_but_not_adjust(self):
        lot = self.make_lot()
        client = self.api_for(self.auditor_user)
        self.assertEqual(client.get("/api/v1/stock-movements/").status_code, 200)
        self.assertEqual(
            client.post(
                "/api/v1/stock-adjustments/",
                {"lot": lot.pk, "quantity_delta": -1, "reason": "x"},
                format="json",
            ).status_code,
            403,
        )

"""Pruebas de la API de ventas.

Lo importante: el servidor decide precio, stock, lote y total. El cliente solo
dice "que" y "cuanto". Cualquier campo de precio que envie se ignora.
"""

from uuid import uuid4

from tests.base import BaseAPITestCase

SALES_URL = "/api/v1/sales/"


class SalesApiTests(BaseAPITestCase):
    def sale_payload(self, product_id, quantity=1, received="50.00", request_id=None):
        return {
            "client_request_id": str(request_id or uuid4()),
            "items": [{"product_id": product_id, "quantity": quantity}],
            "payment": {"method": "EFECTIVO", "received_amount": received},
        }

    def test_sale_is_created_with_server_side_prices(self):
        lot = self.make_lot(quantity=10)
        response = self.api_for(self.cashier_user).post(
            SALES_URL, self.sale_payload(lot.product_id, quantity=2), format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["number"], "00000001")
        self.assertEqual(response.data["total"], "24.00")
        self.assertEqual(response.headers["X-Idempotent-Replay"], "false")

        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 8)

    def test_client_cannot_choose_the_price(self):
        lot = self.make_lot()
        payload = self.sale_payload(lot.product_id, quantity=1)
        # Intento de manipular el precio desde el navegador.
        payload["items"][0]["unit_price"] = "0.01"
        payload["total"] = "0.01"

        response = self.api_for(self.cashier_user).post(SALES_URL, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["total"], "12.00")
        self.assertEqual(response.data["items"][0]["unit_price"], "12.00")

    def test_insufficient_stock_returns_409_with_a_stable_code(self):
        lot = self.make_lot(quantity=10)
        response = self.api_for(self.cashier_user).post(
            SALES_URL, self.sale_payload(lot.product_id, quantity=99), format="json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "insufficient_stock")
        self.assertEqual(response.data["error"]["details"]["requested"], 99)

        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 10)

    def test_replaying_the_same_request_does_not_duplicate_the_sale(self):
        lot = self.make_lot(quantity=10)
        request_id = uuid4()
        client = self.api_for(self.cashier_user)

        first = client.post(
            SALES_URL, self.sale_payload(lot.product_id, 1, request_id=request_id), format="json"
        )
        second = client.post(
            SALES_URL, self.sale_payload(lot.product_id, 1, request_id=request_id), format="json"
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.headers["X-Idempotent-Replay"], "true")
        self.assertEqual(second.data["number"], first.data["number"])

        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 9)

    def test_receipt_has_no_cost_and_no_margin(self):
        lot = self.make_lot()
        client = self.api_for(self.cashier_user)
        sale = client.post(SALES_URL, self.sale_payload(lot.product_id, 1), format="json").data

        receipt = client.get(f"/api/v1/receipts/{sale['number']}/")
        self.assertEqual(receipt.status_code, 200)

        body = str(receipt.data)
        self.assertNotIn("unit_cost", body)
        self.assertNotIn("margin", body)
        self.assertEqual(
            set(receipt.data["items"][0]),
            {"product_name", "quantity", "unit_price", "line_total"},
        )
        self.assertEqual(receipt.data["total"], "12.00")

    def test_sale_detail_shows_margin_to_staff(self):
        lot = self.make_lot()
        client = self.api_for(self.cashier_user)
        created = client.post(SALES_URL, self.sale_payload(lot.product_id, 2), format="json").data

        detail = client.get(f"{SALES_URL}{created['id']}/")
        self.assertEqual(detail.status_code, 200)
        item = detail.data["items"][0]
        self.assertEqual(item["unit_cost"], "8.0000")
        self.assertEqual(item["margin"], "8.00")  # (12.00 - 8.00) x 2

    def test_cashier_only_sees_their_own_sales(self):
        lot = self.make_lot()
        sale = (
            self.api_for(self.cashier_user)
            .post(SALES_URL, self.sale_payload(lot.product_id, 1), format="json")
            .data
        )

        mine = self.api_for(self.cashier_user).get(SALES_URL)
        self.assertEqual([row["id"] for row in mine.data["results"]], [sale["id"]])

        theirs = self.api_for(self.other_cashier).get(SALES_URL)
        self.assertEqual(theirs.data["results"], [])

    def test_regent_sees_sales_from_the_whole_team(self):
        lot = self.make_lot()
        self.api_for(self.cashier_user).post(
            SALES_URL, self.sale_payload(lot.product_id, 1), format="json"
        )

        response = self.api_for(self.regent_user).get(SALES_URL)
        self.assertEqual(len(response.data["results"]), 1)

    def test_auditor_can_read_sales_but_not_create_them(self):
        lot = self.make_lot()
        client = self.api_for(self.auditor_user)
        self.assertEqual(client.get(SALES_URL).status_code, 200)

        response = client.post(SALES_URL, self.sale_payload(lot.product_id, 1), format="json")
        self.assertEqual(response.status_code, 403)

    def test_warehouse_user_cannot_access_sales(self):
        response = self.api_for(self.warehouse_user).get(SALES_URL)
        self.assertEqual(response.status_code, 403)

    def test_card_payment_does_not_require_received_amount(self):
        lot = self.make_lot()
        payload = self.sale_payload(lot.product_id, 1)
        payload["payment"] = {"method": "TARJETA"}

        response = self.api_for(self.cashier_user).post(SALES_URL, payload, format="json")

        self.assertEqual(response.status_code, 201)
        payment = response.data["payments"][0]
        self.assertEqual(payment["change_amount"], "0.00")

    def test_cash_shortfall_is_rejected_with_409(self):
        lot = self.make_lot(quantity=10)
        response = self.api_for(self.cashier_user).post(
            SALES_URL, self.sale_payload(lot.product_id, 1, received="5.00"), format="json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "insufficient_payment")
        lot.refresh_from_db()
        self.assertEqual(lot.current_quantity, 10)

    def test_selling_zero_units_is_a_validation_error(self):
        lot = self.make_lot()
        response = self.api_for(self.cashier_user).post(
            SALES_URL, self.sale_payload(lot.product_id, 0), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")

    def test_empty_cart_is_rejected(self):
        lot = self.make_lot()
        payload = self.sale_payload(lot.product_id, 1)
        payload["items"] = []

        response = self.api_for(self.cashier_user).post(SALES_URL, payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_expired_lot_is_not_sold(self):
        expired = self.make_lot(days_to_expiry=-3, quantity=5, batch="VENCIDO")

        response = self.api_for(self.cashier_user).post(
            SALES_URL, self.sale_payload(expired.product_id, 1), format="json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "insufficient_stock")
        expired.refresh_from_db()
        self.assertEqual(expired.current_quantity, 5)

    def test_lot_expiring_today_can_be_sold(self):
        today_lot = self.make_lot(days_to_expiry=0, quantity=5, batch="HOY")

        response = self.api_for(self.cashier_user).post(
            SALES_URL, self.sale_payload(today_lot.product_id, 1), format="json"
        )

        self.assertEqual(response.status_code, 201)
        today_lot.refresh_from_db()
        self.assertEqual(today_lot.current_quantity, 4)

    def test_product_lookup_shows_stock_and_fefo_lots(self):
        later = self.make_lot(days_to_expiry=200, quantity=5, batch="L-200")
        sooner = self.make_lot(days_to_expiry=20, quantity=7, batch="L-020")
        self.assertGreater(later.expiry_date, sooner.expiry_date)

        response = self.api_for(self.cashier_user).get(
            "/api/v1/products/lookup/", {"barcode": sooner.product.barcode}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stock"], 12)
        self.assertEqual([lot["batch_number"] for lot in response.data["lots"]], ["L-020", "L-200"])

    def test_product_lookup_by_text_finds_by_name(self):
        response = self.api_for(self.cashier_user).get("/api/v1/products/lookup/", {"q": "paracet"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn("Paracetamol", response.data[0]["display_name"])

    def test_product_lookup_requires_a_criterion(self):
        response = self.api_for(self.cashier_user).get("/api/v1/products/lookup/")
        self.assertEqual(response.status_code, 400)

    def test_product_lookup_with_unknown_barcode_is_404(self):
        response = self.api_for(self.cashier_user).get(
            "/api/v1/products/lookup/", {"barcode": "0000"}
        )
        self.assertEqual(response.status_code, 404)

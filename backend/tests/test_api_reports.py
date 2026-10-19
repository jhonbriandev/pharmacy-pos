"""Pruebas del dashboard, las exportaciones y la auditoria."""

from uuid import uuid4

from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditEvent
from apps.audit.services import record_event
from tests.base import BaseAPITestCase
from tests.factories import PASSWORD


class ReportsApiTests(BaseAPITestCase):
    def sell(self, client, product_id, quantity=1):
        return client.post(
            "/api/v1/sales/",
            {
                "client_request_id": str(uuid4()),
                "items": [{"product_id": product_id, "quantity": quantity}],
                "payment": {"method": "EFECTIVO", "received_amount": "100.00"},
            },
            format="json",
        )

    def test_dashboard_reports_sales_totals(self):
        lot = self.make_lot(quantity=10)
        cashier = self.api_for(self.cashier_user)
        self.assertEqual(self.sell(cashier, lot.product_id, 2).status_code, 201)
        self.assertEqual(self.sell(cashier, lot.product_id, 1).status_code, 201)

        response = self.api_for(self.admin_user).get("/api/v1/reports/dashboard/")

        self.assertEqual(response.status_code, 200)
        summary = response.data["summary"]
        self.assertEqual(summary["sales_count"], 2)
        self.assertEqual(summary["sales_total"], "36.00")
        self.assertEqual(summary["average_ticket"], "18.00")

    def test_dashboard_margin_uses_historical_cost(self):
        lot = self.make_lot(quantity=10, cost="8.0000")
        self.sell(self.api_for(self.cashier_user), lot.product_id, 2)

        response = self.api_for(self.admin_user).get("/api/v1/reports/dashboard/")
        margin = response.data["gross_margin"]

        self.assertEqual(margin["revenue"], "24.00")
        self.assertEqual(margin["cost"], "16.00")
        self.assertEqual(margin["margin"], "8.00")
        self.assertEqual(margin["margin_percentage"], "33.33")

    def test_dashboard_is_forbidden_to_cashiers(self):
        response = self.api_for(self.cashier_user).get("/api/v1/reports/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_dashboard_accepts_an_empty_period(self):
        response = self.api_for(self.admin_user).get(
            "/api/v1/reports/dashboard/",
            {"date_from": "2020-01-01", "date_to": "2020-01-31"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["sales_count"], 0)
        self.assertEqual(response.data["summary"]["average_ticket"], "0.00")

    def test_dashboard_rejects_a_malformed_date(self):
        response = self.api_for(self.admin_user).get(
            "/api/v1/reports/dashboard/", {"date_from": "01/01/2020"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "invalid_date")

    def test_dashboard_includes_expiring_and_expired_lots(self):
        self.make_lot(days_to_expiry=15, quantity=5, batch="PRONTO")
        self.make_lot(days_to_expiry=-15, quantity=5, batch="VENCIDO")

        response = self.api_for(self.admin_user).get("/api/v1/reports/dashboard/")

        self.assertEqual(
            [row["batch_number"] for row in response.data["expiring_lots"]], ["PRONTO"]
        )
        self.assertEqual(
            [row["batch_number"] for row in response.data["expired_lots"]], ["VENCIDO"]
        )

    def test_low_stock_alert_appears_on_dashboard(self):
        response = self.api_for(self.admin_user).get("/api/v1/reports/dashboard/")
        self.assertIn(self.product.pk, {row["product_id"] for row in response.data["low_stock"]})

    def test_sales_export_is_a_utf8_csv_with_bom(self):
        lot = self.make_lot()
        self.sell(self.api_for(self.cashier_user), lot.product_id, 1)

        response = self.api_for(self.admin_user).get("/api/v1/reports/exports/sales.csv")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        content = response.content.decode("utf-8")
        self.assertTrue(content.startswith("\ufeff"))
        self.assertIn("numero;fecha;hora;vendedor", content)
        self.assertIn("00000001", content)
        self.assertIn("12.00", content)

    def test_movements_export_requires_inventory_access(self):
        self.assertEqual(
            self.api_for(self.cashier_user)
            .get("/api/v1/reports/exports/movements.csv")
            .status_code,
            403,
        )
        self.assertEqual(
            self.api_for(self.warehouse_user)
            .get("/api/v1/reports/exports/movements.csv")
            .status_code,
            200,
        )

    def test_audit_events_are_visible_to_admin_and_auditor(self):
        record_event(
            action=AuditAction.ROLE_CHANGED,
            entity=self.cashier_user,
            actor=self.admin_user,
            before={"role": "CAJERO"},
            after={"role": "ALMACEN"},
            request=None,
        )

        for user in (self.admin_user, self.auditor_user):
            response = self.api_for(user).get("/api/v1/audit-events/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["results"][0]["action"], AuditAction.ROLE_CHANGED)

    def test_audit_events_are_hidden_from_other_roles(self):
        for user in (self.regent_user, self.warehouse_user, self.cashier_user):
            self.assertEqual(self.api_for(user).get("/api/v1/audit-events/").status_code, 403)

    def test_audit_is_immutable(self):
        event = record_event(
            action=AuditAction.LOGIN_SUCCESS,
            entity=self.cashier_user,
            actor=self.cashier_user,
            request=None,
        )

        # No hay endpoints de escritura: el router solo expone list/retrieve.
        client = self.api_for(self.admin_user)
        self.assertEqual(client.post("/api/v1/audit-events/", {}, format="json").status_code, 405)
        self.assertEqual(client.delete(f"/api/v1/audit-events/{event.pk}/").status_code, 405)

    def test_login_success_is_audited(self):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").data["csrfToken"]
        client.post(
            "/api/v1/auth/login/",
            {"username": self.cashier_user.username, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertTrue(AuditEvent.objects.filter(action=AuditAction.LOGIN_SUCCESS).exists())

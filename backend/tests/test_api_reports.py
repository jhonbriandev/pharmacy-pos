"""Pruebas del dashboard, las exportaciones y la auditoria."""

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditEvent
from apps.audit.services import record_event

pytestmark = pytest.mark.django_db


def api_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def sell(client, product_id, quantity=1):
    from uuid import uuid4

    return client.post(
        "/api/v1/sales/",
        {
            "client_request_id": str(uuid4()),
            "items": [{"product_id": product_id, "quantity": quantity}],
            "payment": {"method": "EFECTIVO", "received_amount": "100.00"},
        },
        format="json",
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def test_dashboard_reports_sales_totals(stocked_lot, cashier_user, admin_user):
    client = api_for(cashier_user)
    assert sell(client, stocked_lot.product_id, 2).status_code == 201
    assert sell(client, stocked_lot.product_id, 1).status_code == 201

    response = api_for(admin_user).get("/api/v1/reports/dashboard/")

    assert response.status_code == 200
    summary = response.data["summary"]
    assert summary["sales_count"] == 2
    assert summary["sales_total"] == "36.00"
    assert summary["average_ticket"] == "18.00"


def test_dashboard_margin_uses_historical_cost(stocked_lot, cashier_user, admin_user):
    sell(api_for(cashier_user), stocked_lot.product_id, 2)

    response = api_for(admin_user).get("/api/v1/reports/dashboard/")
    margin = response.data["gross_margin"]

    assert margin["revenue"] == "24.00"
    assert margin["cost"] == "16.00"
    assert margin["margin"] == "8.00"
    assert margin["margin_percentage"] == "33.33"


def test_dashboard_is_forbidden_to_cashiers(cashier_user):
    assert api_for(cashier_user).get("/api/v1/reports/dashboard/").status_code == 403


def test_dashboard_accepts_an_empty_period(admin_user):
    response = api_for(admin_user).get(
        "/api/v1/reports/dashboard/", {"date_from": "2020-01-01", "date_to": "2020-01-31"}
    )
    assert response.status_code == 200
    assert response.data["summary"]["sales_count"] == 0
    assert response.data["summary"]["average_ticket"] == "0.00"


def test_dashboard_rejects_a_malformed_date(admin_user):
    response = api_for(admin_user).get("/api/v1/reports/dashboard/", {"date_from": "01/01/2020"})
    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_date"


def test_dashboard_includes_expiring_and_expired_lots(lot_factory, admin_user):
    lot_factory(days_to_expiry=15, quantity=5, batch="PRONTO")
    lot_factory(days_to_expiry=-15, quantity=5, batch="VENCIDO")

    response = api_for(admin_user).get("/api/v1/reports/dashboard/")

    assert [row["batch_number"] for row in response.data["expiring_lots"]] == ["PRONTO"]
    assert [row["batch_number"] for row in response.data["expired_lots"]] == ["VENCIDO"]


def test_low_stock_alert_appears_on_dashboard(product, admin_user):
    response = api_for(admin_user).get("/api/v1/reports/dashboard/")
    assert product.pk in {row["product_id"] for row in response.data["low_stock"]}


# ---------------------------------------------------------------------------
# Exportaciones
# ---------------------------------------------------------------------------


def test_sales_export_is_a_utf8_csv_with_bom(stocked_lot, cashier_user, admin_user):
    sell(api_for(cashier_user), stocked_lot.product_id, 1)

    response = api_for(admin_user).get("/api/v1/reports/exports/sales.csv")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    content = response.content.decode("utf-8")
    assert content.startswith("\ufeff")
    assert "numero;fecha;hora;vendedor" in content
    assert "00000001" in content
    assert "12.00" in content


def test_movements_export_requires_inventory_access(cashier_user, warehouse_user):
    assert api_for(cashier_user).get("/api/v1/reports/exports/movements.csv").status_code == 403
    assert api_for(warehouse_user).get("/api/v1/reports/exports/movements.csv").status_code == 200


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------


def test_audit_events_are_visible_to_admin_and_auditor(db, admin_user, auditor_user, cashier_user):
    record_event(
        action=AuditAction.ROLE_CHANGED,
        entity=cashier_user,
        actor=admin_user,
        before={"role": "CAJERO"},
        after={"role": "ALMACEN"},
        request=None,
    )

    for user in (admin_user, auditor_user):
        response = api_for(user).get("/api/v1/audit-events/")
        assert response.status_code == 200
        assert response.data["results"][0]["action"] == AuditAction.ROLE_CHANGED


def test_audit_events_are_hidden_from_other_roles(db, regent_user, warehouse_user, cashier_user):
    for user in (regent_user, warehouse_user, cashier_user):
        assert api_for(user).get("/api/v1/audit-events/").status_code == 403


def test_audit_is_immutable(db, admin_user, cashier_user):
    event = record_event(
        action=AuditAction.LOGIN_SUCCESS,
        entity=cashier_user,
        actor=cashier_user,
        request=None,
    )

    # No hay endpoints de escritura: el router solo expone list/retrieve.
    client = api_for(admin_user)
    assert client.post("/api/v1/audit-events/", {}, format="json").status_code == 405
    assert client.delete(f"/api/v1/audit-events/{event.pk}/").status_code == 405


def test_login_success_is_audited(cashier_user):
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf/").data["csrfToken"]
    client.post(
        "/api/v1/auth/login/",
        {"username": cashier_user.username, "password": "PruebaSegura123"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert AuditEvent.objects.filter(action=AuditAction.LOGIN_SUCCESS).exists()

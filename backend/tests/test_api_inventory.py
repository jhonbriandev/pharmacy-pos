"""Pruebas de la API de inventario: entradas, ajustes, fraccionamiento y lotes."""

from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.inventory.models import Lot, StockMovement
from apps.inventory.services import today

pytestmark = pytest.mark.django_db


def api_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def entry_payload(product, *, batch="ENT-API-01", quantity=10, days=365):
    return {
        "client_request_id": "6f1c1f5e-3b1f-4c9e-9a1e-2b8c7d6e5f40",
        "supplier": "Distribuidora Demo",
        "document_number": "F001-0001",
        "received_at": today().isoformat(),
        "items": [
            {
                "product": product.pk,
                "batch_number": batch,
                "expiry_date": (today() + timedelta(days=days)).isoformat(),
                "quantity": quantity,
                "cost_price": "8.5000",
            }
        ],
    }


def test_stock_entry_creates_lot_and_movement(product, warehouse_user):
    response = api_for(warehouse_user).post(
        "/api/v1/stock-entries/", entry_payload(product), format="json"
    )

    assert response.status_code == 201
    lot = Lot.objects.get(batch_number="ENT-API-01")
    assert lot.current_quantity == 10
    assert StockMovement.objects.filter(lot=lot).count() == 1
    assert product.refresh_from_db() is None
    assert product.last_cost == Decimal("8.5000")


def test_stock_entry_replay_returns_200_and_does_not_duplicate(product, warehouse_user):
    client = api_for(warehouse_user)
    payload = entry_payload(product)

    first = client.post("/api/v1/stock-entries/", payload, format="json")
    second = client.post("/api/v1/stock-entries/", payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["X-Idempotent-Replay"] == "true"
    assert Lot.objects.get(batch_number="ENT-API-01").current_quantity == 10


def test_stock_entry_rejects_duplicate_batch_lines(product, warehouse_user):
    payload = entry_payload(product)
    payload["items"].append(payload["items"][0])

    response = api_for(warehouse_user).post("/api/v1/stock-entries/", payload, format="json")
    assert response.status_code == 400


def test_cashier_cannot_create_stock_entries(product, cashier_user):
    response = api_for(cashier_user).post(
        "/api/v1/stock-entries/", entry_payload(product), format="json"
    )
    assert response.status_code == 403


def test_adjustment_requires_manager_role(stocked_lot, warehouse_user, regent_user):
    payload = {"lot": stocked_lot.pk, "quantity_delta": -1, "reason": "Averia"}

    assert (
        api_for(warehouse_user)
        .post("/api/v1/stock-adjustments/", payload, format="json")
        .status_code
        == 403
    )

    response = api_for(regent_user).post("/api/v1/stock-adjustments/", payload, format="json")
    assert response.status_code == 201


def test_adjustment_rejects_unknown_lot(admin_user):
    response = api_for(admin_user).post(
        "/api/v1/stock-adjustments/",
        {"lot": 999999, "quantity_delta": -1, "reason": "Averia"},
        format="json",
    )
    assert response.status_code == 400


def test_adjustment_cannot_leave_negative_stock(stocked_lot, admin_user):
    response = api_for(admin_user).post(
        "/api/v1/stock-adjustments/",
        {"lot": stocked_lot.pk, "quantity_delta": -99, "reason": "Averia"},
        format="json",
    )
    assert response.status_code == 409
    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 10


def test_lot_block_prevents_sales(stocked_lot, regent_user, cashier_user):
    response = api_for(regent_user).post(
        f"/api/v1/lots/{stocked_lot.pk}/block/",
        {"reason": "Sospecha de falsificacion"},
        format="json",
    )
    assert response.status_code == 200

    stock = api_for(cashier_user).post(
        "/api/v1/sales/",
        {
            "client_request_id": "11111111-1111-1111-1111-111111111111",
            "items": [{"product_id": stocked_lot.product_id, "quantity": 1}],
            "payment": {"method": "EFECTIVO", "received_amount": "20.00"},
        },
        format="json",
    )
    assert stock.status_code == 409


def test_expiring_lots_endpoint_excludes_expired(lot_factory, warehouse_user):
    lot_factory(days_to_expiry=10, quantity=5, batch="PRONTO")
    lot_factory(days_to_expiry=400, quantity=5, batch="LEJOS")
    lot_factory(days_to_expiry=-10, quantity=5, batch="VENCIDO")

    response = api_for(warehouse_user).get("/api/v1/lots/expiring/", {"within_days": 30})

    assert response.status_code == 200
    assert [row["batch_number"] for row in response.data] == ["PRONTO"]


def test_expired_lots_endpoint_lists_only_expired(lot_factory, warehouse_user):
    lot_factory(days_to_expiry=10, quantity=5, batch="PRONTO")
    lot_factory(days_to_expiry=-10, quantity=5, batch="VENCIDO")

    response = api_for(warehouse_user).get("/api/v1/lots/expired/")
    assert [row["batch_number"] for row in response.data] == ["VENCIDO"]


def test_fractionation_endpoint_splits_a_box(product, warehouse_user):
    from apps.catalog.models import PresentationType, Product, UnitConversion

    blister = Product.objects.create(
        group=product.group,
        presentation=PresentationType.BLISTER,
        presentation_detail="x 10",
        barcode="7000000000100",
        sale_price=Decimal("1.80"),
    )
    UnitConversion.objects.create(group=product.group, source=product, target=blister, factor=10)

    created = api_for(warehouse_user).post(
        "/api/v1/stock-entries/",
        entry_payload(product, batch="CAJA-FRAC", quantity=4),
        format="json",
    )
    assert created.status_code == 201
    box_lot = Lot.objects.get(batch_number="CAJA-FRAC")

    response = api_for(warehouse_user).post(
        "/api/v1/stock-fractionations/",
        {
            "source_lot": box_lot.pk,
            "quantity": 1,
        },
        format="json",
    )

    assert response.status_code == 201
    box_lot.refresh_from_db()
    assert box_lot.current_quantity == 3
    # RF4: el lote destino conserva el numero de lote del origen.
    blister_lot = Lot.objects.get(product=blister, batch_number="CAJA-FRAC")
    assert blister_lot.current_quantity == 10


def test_consistency_endpoint_reports_ok(stocked_lot, admin_user):
    response = api_for(admin_user).get("/api/v1/inventory/consistency/")
    assert response.status_code == 200
    assert response.data == {"consistent": True, "issues_count": 0, "issues": []}


def test_low_stock_endpoint_flags_products_below_minimum(product, warehouse_user):
    # product.min_stock = 5 y no tiene lotes: debe aparecer.
    response = api_for(warehouse_user).get("/api/v1/products/low-stock/")

    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [product.pk]
    assert response.data[0]["stock"] == 0


def test_stock_movements_are_read_only(stocked_lot, warehouse_user):
    client = api_for(warehouse_user)
    assert client.get("/api/v1/stock-movements/").status_code == 200
    assert client.post("/api/v1/stock-movements/", {}, format="json").status_code == 405


def test_auditor_can_read_movements_but_not_adjust(stocked_lot, auditor_user):
    client = api_for(auditor_user)
    assert client.get("/api/v1/stock-movements/").status_code == 200
    assert (
        client.post(
            "/api/v1/stock-adjustments/",
            {"lot": stocked_lot.pk, "quantity_delta": -1, "reason": "x"},
            format="json",
        ).status_code
        == 403
    )

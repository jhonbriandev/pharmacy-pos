"""Pruebas de la API de ventas.

Lo importante: el servidor decide precio, stock, lote y total. El cliente solo
dice "que" y "cuanto". Cualquier campo de precio que envie se ignora.
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

SALES_URL = "/api/v1/sales/"


def api_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def sale_payload(product_id: int, quantity: int = 1, received="50.00", request_id=None):
    return {
        "client_request_id": str(request_id or uuid4()),
        "items": [{"product_id": product_id, "quantity": quantity}],
        "payment": {"method": "EFECTIVO", "received_amount": received},
    }


pytestmark = pytest.mark.django_db


def test_sale_is_created_with_server_side_prices(stocked_lot, cashier_user):
    response = api_for(cashier_user).post(
        SALES_URL, sale_payload(stocked_lot.product_id, quantity=2), format="json"
    )

    assert response.status_code == 201
    assert response.data["number"] == "00000001"
    assert response.data["total"] == "24.00"
    assert response.headers["X-Idempotent-Replay"] == "false"

    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 8


def test_client_cannot_choose_the_price(stocked_lot, cashier_user):
    payload = sale_payload(stocked_lot.product_id, quantity=1)
    # Intento de manipular el precio desde el navegador.
    payload["items"][0]["unit_price"] = "0.01"
    payload["total"] = "0.01"

    response = api_for(cashier_user).post(SALES_URL, payload, format="json")

    assert response.status_code == 201
    assert response.data["total"] == "12.00"
    assert response.data["items"][0]["unit_price"] == "12.00"


def test_insufficient_stock_returns_409_with_a_stable_code(stocked_lot, cashier_user):
    response = api_for(cashier_user).post(
        SALES_URL, sale_payload(stocked_lot.product_id, quantity=99), format="json"
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "insufficient_stock"
    assert response.data["error"]["details"]["requested"] == 99

    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 10


def test_replaying_the_same_request_does_not_duplicate_the_sale(stocked_lot, cashier_user):
    request_id = uuid4()
    client = api_for(cashier_user)

    first = client.post(
        SALES_URL, sale_payload(stocked_lot.product_id, 1, request_id=request_id), format="json"
    )
    second = client.post(
        SALES_URL, sale_payload(stocked_lot.product_id, 1, request_id=request_id), format="json"
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["X-Idempotent-Replay"] == "true"
    assert second.data["number"] == first.data["number"]

    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 9


def test_receipt_has_no_cost_and_no_margin(stocked_lot, cashier_user):
    client = api_for(cashier_user)
    sale = client.post(SALES_URL, sale_payload(stocked_lot.product_id, 1), format="json").data

    receipt = client.get(f"/api/v1/receipts/{sale['number']}/")
    assert receipt.status_code == 200

    body = str(receipt.data)
    assert "unit_cost" not in body
    assert "margin" not in body
    assert set(receipt.data["items"][0]) == {
        "product_name",
        "quantity",
        "unit_price",
        "line_total",
    }
    assert receipt.data["total"] == "12.00"


def test_sale_detail_shows_margin_to_staff(stocked_lot, cashier_user):
    client = api_for(cashier_user)
    created = client.post(SALES_URL, sale_payload(stocked_lot.product_id, 2), format="json").data

    detail = client.get(f"{SALES_URL}{created['id']}/")
    assert detail.status_code == 200
    item = detail.data["items"][0]
    assert item["unit_cost"] == "8.0000"
    assert item["margin"] == "8.00"  # (12.00 - 8.00) x 2


def test_cashier_only_sees_their_own_sales(stocked_lot, cashier_user, other_cashier):
    sale = (
        api_for(cashier_user)
        .post(SALES_URL, sale_payload(stocked_lot.product_id, 1), format="json")
        .data
    )

    mine = api_for(cashier_user).get(SALES_URL)
    assert [row["id"] for row in mine.data["results"]] == [sale["id"]]

    theirs = api_for(other_cashier).get(SALES_URL)
    assert theirs.data["results"] == []


def test_regent_sees_sales_from_the_whole_team(stocked_lot, cashier_user, regent_user):
    api_for(cashier_user).post(SALES_URL, sale_payload(stocked_lot.product_id, 1), format="json")

    response = api_for(regent_user).get(SALES_URL)
    assert len(response.data["results"]) == 1


def test_auditor_can_read_sales_but_not_create_them(stocked_lot, auditor_user):
    client = api_for(auditor_user)
    assert client.get(SALES_URL).status_code == 200

    response = client.post(SALES_URL, sale_payload(stocked_lot.product_id, 1), format="json")
    assert response.status_code == 403


def test_warehouse_user_cannot_access_sales(stocked_lot, warehouse_user):
    response = api_for(warehouse_user).get(SALES_URL)
    assert response.status_code == 403


def test_card_payment_does_not_require_received_amount(stocked_lot, cashier_user):
    payload = sale_payload(stocked_lot.product_id, 1)
    payload["payment"] = {"method": "TARJETA"}

    response = api_for(cashier_user).post(SALES_URL, payload, format="json")

    assert response.status_code == 201
    payment = response.data["payments"][0]
    assert payment["change_amount"] == "0.00"


def test_cash_shortfall_is_rejected_with_409(stocked_lot, cashier_user):
    response = api_for(cashier_user).post(
        SALES_URL, sale_payload(stocked_lot.product_id, 1, received="5.00"), format="json"
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "insufficient_payment"
    stocked_lot.refresh_from_db()
    assert stocked_lot.current_quantity == 10


def test_selling_zero_units_is_a_validation_error(stocked_lot, cashier_user):
    response = api_for(cashier_user).post(
        SALES_URL, sale_payload(stocked_lot.product_id, 0), format="json"
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_empty_cart_is_rejected(stocked_lot, cashier_user):
    payload = sale_payload(stocked_lot.product_id, 1)
    payload["items"] = []

    response = api_for(cashier_user).post(SALES_URL, payload, format="json")
    assert response.status_code == 400


def test_expired_lot_is_not_sold(lot_factory, cashier_user):
    expired = lot_factory(days_to_expiry=-3, quantity=5, batch="VENCIDO")

    response = api_for(cashier_user).post(
        SALES_URL, sale_payload(expired.product_id, 1), format="json"
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "insufficient_stock"
    expired.refresh_from_db()
    assert expired.current_quantity == 5


def test_lot_expiring_today_can_be_sold(lot_factory, cashier_user):
    today_lot = lot_factory(days_to_expiry=0, quantity=5, batch="HOY")

    response = api_for(cashier_user).post(
        SALES_URL, sale_payload(today_lot.product_id, 1), format="json"
    )

    assert response.status_code == 201
    today_lot.refresh_from_db()
    assert today_lot.current_quantity == 4


def test_product_lookup_shows_stock_and_fefo_lots(lot_factory, cashier_user):
    later = lot_factory(days_to_expiry=200, quantity=5, batch="L-200")
    sooner = lot_factory(days_to_expiry=20, quantity=7, batch="L-020")
    assert later.expiry_date > sooner.expiry_date

    client = api_for(cashier_user)
    response = client.get("/api/v1/products/lookup/", {"barcode": sooner.product.barcode})

    assert response.status_code == 200
    assert response.data["stock"] == 12
    assert [lot["batch_number"] for lot in response.data["lots"]] == ["L-020", "L-200"]


def test_product_lookup_by_text_finds_by_name(product, cashier_user):
    response = api_for(cashier_user).get("/api/v1/products/lookup/", {"q": "paracet"})
    assert response.status_code == 200
    assert len(response.data) == 1
    assert "Paracetamol" in response.data[0]["display_name"]


def test_product_lookup_requires_a_criterion(cashier_user):
    response = api_for(cashier_user).get("/api/v1/products/lookup/")
    assert response.status_code == 400


def test_product_lookup_with_unknown_barcode_is_404(cashier_user):
    response = api_for(cashier_user).get("/api/v1/products/lookup/", {"barcode": "0000"})
    assert response.status_code == 404

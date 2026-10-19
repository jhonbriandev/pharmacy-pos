"""Pruebas de la API del catalogo.

El IGV es un dato fijo de la farmacia (18%) y va incluido en el precio de
venta: la API lo expone pero no permite cambiarlo por producto.
"""

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Product

pytestmark = pytest.mark.django_db


def api_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def product_payload(product, **overrides):
    payload = {
        "group": product.group_id,
        "presentation": "UNIDAD",
        "presentation_detail": "x 1",
        "barcode": "7000000000999",
        "unit_label": "unidad",
        "sale_price": "2.50",
        "min_stock": 0,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_product_create_forces_the_igv_to_18(product, admin_user):
    response = api_for(admin_user).post(
        "/api/v1/products/",
        product_payload(product, tax_rate="0.00"),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["tax_rate"] == "18.00"
    created = Product.objects.get(pk=response.data["id"])
    assert created.tax_rate == 18


def test_product_update_cannot_change_the_igv(product, admin_user):
    response = api_for(admin_user).patch(
        f"/api/v1/products/{product.pk}/",
        {"tax_rate": "10.00"},
        format="json",
    )

    assert response.status_code == 200
    product.refresh_from_db()
    assert product.tax_rate == 18
    assert response.data["tax_rate"] == "18.00"

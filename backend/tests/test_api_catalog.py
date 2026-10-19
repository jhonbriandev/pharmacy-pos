"""Pruebas de la API del catalogo.

El IGV es un dato fijo de la farmacia (18%) y va incluido en el precio de
venta: la API lo expone pero no permite cambiarlo por producto.
"""

from apps.catalog.models import Product
from tests.base import BaseAPITestCase


class CatalogApiTests(BaseAPITestCase):
    def product_payload(self, **overrides):
        payload = {
            "group": self.product.group_id,
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

    def test_product_create_forces_the_igv_to_18(self):
        response = self.api_for(self.admin_user).post(
            "/api/v1/products/",
            self.product_payload(tax_rate="0.00"),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["tax_rate"], "18.00")
        created = Product.objects.get(pk=response.data["id"])
        self.assertEqual(created.tax_rate, 18)

    def test_product_update_cannot_change_the_igv(self):
        response = self.api_for(self.admin_user).patch(
            f"/api/v1/products/{self.product.pk}/",
            {"tax_rate": "10.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.tax_rate, 18)
        self.assertEqual(response.data["tax_rate"], "18.00")

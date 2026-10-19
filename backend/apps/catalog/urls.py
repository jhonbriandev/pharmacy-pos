"""Rutas del catalogo."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.catalog.views import (
    ActiveIngredientViewSet,
    CategoryViewSet,
    LaboratoryViewSet,
    ProductGroupViewSet,
    ProductLookupView,
    ProductViewSet,
    UnitConversionViewSet,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("product-groups", ProductGroupViewSet, basename="product-group")
router.register("laboratories", LaboratoryViewSet, basename="laboratory")
router.register("categories", CategoryViewSet, basename="category")
router.register("active-ingredients", ActiveIngredientViewSet, basename="active-ingredient")
router.register("unit-conversions", UnitConversionViewSet, basename="unit-conversion")

urlpatterns = [
    # Debe ir antes del router: si no, ``products/lookup/`` se interpreta como
    # el detalle de un producto con pk="lookup".
    path("products/lookup/", ProductLookupView.as_view(), name="product-lookup"),
    *router.urls,
]

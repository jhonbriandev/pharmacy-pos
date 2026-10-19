"""Rutas de inventario."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    ConsistencyView,
    FractionationView,
    LotViewSet,
    StockAdjustmentView,
    StockEntryViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register("stock-entries", StockEntryViewSet, basename="stock-entry")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("lots", LotViewSet, basename="lot")

urlpatterns = [
    *router.urls,
    path("stock-adjustments/", StockAdjustmentView.as_view(), name="stock-adjustment"),
    path("stock-fractionations/", FractionationView.as_view(), name="stock-fractionation"),
    path("inventory/consistency/", ConsistencyView.as_view(), name="inventory-consistency"),
]

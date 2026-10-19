"""Rutas de ventas."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.sales.views import SaleReceiptView, SaleViewSet

router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")

urlpatterns = [
    *router.urls,
    path("receipts/<str:number>/", SaleReceiptView.as_view(), name="receipt-detail"),
]

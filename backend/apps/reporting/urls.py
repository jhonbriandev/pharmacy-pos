"""Rutas de reportes y exportaciones."""

from django.urls import path

from apps.reporting.views import (
    DashboardView,
    MovementsCsvExportView,
    SalesCsvExportView,
    SalesSummaryView,
    TopProductsView,
)

app_name = "reporting"

urlpatterns = [
    path("reports/dashboard/", DashboardView.as_view(), name="dashboard"),
    path("reports/sales-summary/", SalesSummaryView.as_view(), name="sales-summary"),
    path("reports/top-products/", TopProductsView.as_view(), name="top-products"),
    path("reports/exports/sales.csv", SalesCsvExportView.as_view(), name="export-sales"),
    path(
        "reports/exports/movements.csv", MovementsCsvExportView.as_view(), name="export-movements"
    ),
]

"""API de reportes y dashboard."""

import csv
from datetime import date

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanViewDashboard, CanViewInventory
from apps.reporting import services
from apps.sales.models import Sale, SaleStatus


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class DashboardView(APIView):
    """Indicadores del negocio para gerencia y regencia."""

    permission_classes = [CanViewDashboard]

    def get(self, request):
        date_from = _parse_date(request.query_params.get("date_from"))
        date_to = _parse_date(request.query_params.get("date_to"))

        for raw in (request.query_params.get("date_from"), request.query_params.get("date_to")):
            if raw and _parse_date(raw) is None:
                return Response(
                    {
                        "error": {
                            "code": "invalid_date",
                            "message": "Las fechas deben tener el formato AAAA-MM-DD.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(services.dashboard(date_from=date_from, date_to=date_to))


class SalesCsvExportView(APIView):
    """Exportacion de ventas a CSV para conciliacion contable."""

    permission_classes = [CanViewDashboard]

    def get(self, request):
        date_from = _parse_date(request.query_params.get("date_from"))
        date_to = _parse_date(request.query_params.get("date_to"))
        if date_from is None or date_to is None:
            date_from, date_to = services.default_range()

        sales = (
            Sale.objects.filter(
                status=SaleStatus.CONFIRMED,
                created_at__date__gte=date_from,
                created_at__date__lte=date_to,
            )
            .select_related("created_by")
            .prefetch_related("items", "payments")
            .order_by("created_at")
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="ventas_{date_from}_{date_to}.csv"'
        # BOM para que Excel en Windows abra el archivo con acentos correctos.
        response.write("\ufeff")

        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                "numero",
                "fecha",
                "hora",
                "vendedor",
                "dni_vendedor",
                "items",
                "total",
                "medio_pago",
                "monto_recibido",
                "vuelto",
                "referencia",
            ]
        )
        for sale in sales:
            payment = sale.payments.first()
            local_dt = sale.created_at
            writer.writerow(
                [
                    sale.number,
                    local_dt.strftime("%d/%m/%Y"),
                    local_dt.strftime("%H:%M"),
                    sale.created_by.full_name if sale.created_by_id else "",
                    sale.created_by.username if sale.created_by_id else "",
                    sale.items.count(),
                    f"{sale.total:.2f}",
                    payment.get_method_display() if payment else "",
                    f"{payment.received_amount:.2f}" if payment and payment.received_amount else "",
                    f"{payment.change_amount:.2f}" if payment else "",
                    payment.reference if payment else "",
                ]
            )
        return response


class MovementsCsvExportView(APIView):
    """Exportacion del libro mayor de inventario a CSV."""

    permission_classes = [CanViewInventory]

    def get(self, request):
        from apps.inventory.models import StockMovement

        date_from = _parse_date(request.query_params.get("date_from"))
        date_to = _parse_date(request.query_params.get("date_to"))

        movements = StockMovement.objects.select_related(
            "product__group", "lot", "created_by"
        ).order_by("created_at")
        if date_from:
            movements = movements.filter(created_at__date__gte=date_from)
        if date_to:
            movements = movements.filter(created_at__date__lte=date_to)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="movimientos.csv"'
        response.write("\ufeff")

        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                "fecha",
                "hora",
                "tipo",
                "producto",
                "lote",
                "variacion",
                "saldo",
                "motivo",
                "usuario",
            ]
        )
        for movement in movements.iterator():
            writer.writerow(
                [
                    movement.created_at.strftime("%d/%m/%Y"),
                    movement.created_at.strftime("%H:%M"),
                    movement.get_movement_type_display(),
                    movement.product.display_name,
                    movement.lot.batch_number,
                    movement.quantity_delta,
                    movement.balance_after,
                    movement.reason,
                    movement.created_by.full_name if movement.created_by_id else "Sistema",
                ]
            )
        return response


class SalesSummaryView(APIView):
    """Serie de ventas por dia, usuario y medio de pago."""

    permission_classes = [CanViewDashboard]

    def get(self, request):
        date_from = _parse_date(request.query_params.get("date_from"))
        date_to = _parse_date(request.query_params.get("date_to"))
        if date_from is None or date_to is None:
            date_from, date_to = services.default_range()

        rows = (
            Sale.objects.filter(
                status=SaleStatus.CONFIRMED,
                created_at__date__gte=date_from,
                created_at__date__lte=date_to,
            )
            .values(
                "created_at__date",
                "created_by__id",
                "created_by__username",
                "created_by__first_name",
                "created_by__last_name",
            )
            .annotate()
            .order_by("created_at__date")
        )
        data = [
            {
                "date": row["created_at__date"].isoformat(),
                "user_id": row["created_by__id"],
                "username": row["created_by__username"],
                "full_name": (
                    f"{row['created_by__first_name']} {row['created_by__last_name']}".strip()
                    or row["created_by__username"]
                ),
            }
            for row in rows
        ]
        return Response(data)


class TopProductsView(APIView):
    permission_classes = [CanViewDashboard]

    def get(self, request):
        date_from = _parse_date(request.query_params.get("date_from"))
        date_to = _parse_date(request.query_params.get("date_to"))
        if date_from is None or date_to is None:
            date_from, date_to = services.default_range()
        return Response(services.top_products(date_from=date_from, date_to=date_to))

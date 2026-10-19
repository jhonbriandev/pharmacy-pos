"""Agregados del dashboard.

Todo el calculo ocurre en la base de datos: traer las filas a Python para
sumarlas no escala y consume memoria de la instancia gratuita.

Las fechas se interpretan en la zona horaria del negocio (America/Lima). Un
rango "del 1 al 31" incluye las ventas de las 23:50 del dia 31 en hora local,
aunque en UTC ya sea el dia siguiente.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.inventory.models import Lot
from apps.inventory.services import today
from apps.sales.models import PaymentMethod, Sale, SaleItem, SaleStatus

ZERO = Decimal("0.00")


def _money_field():
    return DecimalField(max_digits=14, decimal_places=2)


def default_range() -> tuple[date, date]:
    """Rango por defecto del dashboard: el mes en curso."""
    end = today()
    start = end.replace(day=1)
    return start, end


def sales_summary(*, date_from: date, date_to: date) -> dict:
    """Indicadores de ventas del periodo."""
    sales = Sale.objects.filter(
        status=SaleStatus.CONFIRMED,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )

    totals = sales.aggregate(
        total=Coalesce(Sum("total"), Value(ZERO), output_field=_money_field()),
        count=Count("id"),
    )
    count = totals["count"] or 0
    total = totals["total"] or ZERO

    return {
        "date_from": date_from,
        "date_to": date_to,
        "sales_total": str(total),
        "sales_count": count,
        "average_ticket": str((total / count).quantize(Decimal("0.01")) if count else ZERO),
    }


def sales_by_day(*, date_from: date, date_to: date) -> list[dict]:
    """Serie diaria de ventas, para el grafico del dashboard."""
    rows = (
        Sale.objects.filter(
            status=SaleStatus.CONFIRMED,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .values("created_at__date")
        .annotate(total=Sum("total"), count=Count("id"))
        .order_by("created_at__date")
    )
    return [
        {
            "date": row["created_at__date"].isoformat(),
            "total": str(row["total"] or ZERO),
            "count": row["count"],
        }
        for row in rows
    ]


def sales_by_payment_method(*, date_from: date, date_to: date) -> list[dict]:
    """Desglose por medio de pago."""
    rows = (
        Sale.objects.filter(
            status=SaleStatus.CONFIRMED,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .values("payments__method")
        .annotate(total=Sum("total"), count=Count("id"))
        .order_by("-total")
    )
    labels = dict(PaymentMethod.choices)
    return [
        {
            "method": row["payments__method"],
            "label": labels.get(row["payments__method"], row["payments__method"]),
            "total": str(row["total"] or ZERO),
            "count": row["count"],
        }
        for row in rows
        if row["payments__method"]
    ]


def top_products(*, date_from: date, date_to: date, limit: int = 10) -> list[dict]:
    """Productos mas vendidos por cantidad."""
    rows = (
        SaleItem.objects.filter(
            sale__status=SaleStatus.CONFIRMED,
            sale__created_at__date__gte=date_from,
            sale__created_at__date__lte=date_to,
        )
        .values("product_id", "product_name")
        .annotate(
            quantity=Sum("quantity"),
            total=Coalesce(Sum("line_total"), Value(ZERO), output_field=_money_field()),
        )
        .order_by("-quantity")[:limit]
    )
    return [
        {
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "quantity": row["quantity"],
            "total": str(row["total"] or ZERO),
        }
        for row in rows
    ]


def gross_margin(*, date_from: date, date_to: date) -> dict:
    """Margen bruto del periodo (precio - costo historico de la linea)."""
    rows = SaleItem.objects.filter(
        sale__status=SaleStatus.CONFIRMED,
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
    ).aggregate(
        revenue=Coalesce(Sum("line_total"), Value(ZERO), output_field=_money_field()),
        cost=Coalesce(
            Sum(F("unit_cost") * F("quantity")), Value(ZERO), output_field=_money_field()
        ),
    )
    revenue = (rows["revenue"] or ZERO).quantize(Decimal("0.01"))
    cost = (rows["cost"] or ZERO).quantize(Decimal("0.01"))
    margin = revenue - cost
    percentage = (margin / revenue * 100) if revenue else ZERO
    return {
        "revenue": str(revenue),
        "cost": str(cost),
        "margin": str(margin),
        "margin_percentage": str(percentage.quantize(Decimal("0.01"))),
    }


def low_stock_alerts(*, limit: int = 20) -> list[dict]:
    """Productos activos cuyo stock vendible esta por debajo del minimo."""
    from apps.catalog.models import Product
    from apps.inventory.services import sellable_stock_expression

    products = (
        Product.objects.select_related("group")
        .filter(is_active=True, min_stock__gt=0)
        .annotate(stock=sellable_stock_expression())
        .filter(stock__lt=F("min_stock"))
        .order_by("stock", "group__name")[:limit]
    )
    return [
        {
            "product_id": product.pk,
            "product_name": product.display_name,
            "stock": product.stock,
            "min_stock": product.min_stock,
        }
        for product in products
    ]


def expiring_lots(*, within_days: int = 90, limit: int = 20) -> list[dict]:
    """Lotes con existencias que vencen pronto."""
    start = today()
    end = start + timedelta(days=max(within_days, 0))
    lots = (
        Lot.objects.select_related("product__group")
        .filter(current_quantity__gt=0, expiry_date__gte=start, expiry_date__lte=end)
        .order_by("expiry_date", "id")[:limit]
    )
    return [
        {
            "lot_id": lot.pk,
            "product_name": lot.product.display_name,
            "batch_number": lot.batch_number,
            "expiry_date": lot.expiry_date.isoformat(),
            "days_left": (lot.expiry_date - start).days,
            "quantity": lot.current_quantity,
        }
        for lot in lots
    ]


def expired_lots(*, limit: int = 20) -> list[dict]:
    """Lotes ya vencidos con existencias: hay que darlos de baja."""
    lots = (
        Lot.objects.select_related("product__group")
        .filter(current_quantity__gt=0, expiry_date__lt=today())
        .order_by("expiry_date", "id")[:limit]
    )
    return [
        {
            "lot_id": lot.pk,
            "product_name": lot.product.display_name,
            "batch_number": lot.batch_number,
            "expiry_date": lot.expiry_date.isoformat(),
            "days_overdue": (today() - lot.expiry_date).days,
            "quantity": lot.current_quantity,
        }
        for lot in lots
    ]


def inventory_value() -> dict:
    """Valorizacion del inventario al costo y a precio de venta."""
    rows = Lot.objects.filter(current_quantity__gt=0).aggregate(
        cost=Coalesce(
            Sum(F("current_quantity") * F("cost_price")),
            Value(ZERO),
            output_field=_money_field(),
        ),
        units=Coalesce(Sum("current_quantity"), Value(0)),
    )
    return {
        "units": rows["units"],
        "cost_value": str((rows["cost"] or ZERO).quantize(Decimal("0.01"))),
    }


def dashboard(*, date_from: date | None = None, date_to: date | None = None) -> dict:
    """Todo lo que necesita el dashboard de gerencia en una respuesta."""
    if date_from is None or date_to is None:
        date_from, date_to = default_range()
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    return {
        "period": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        "summary": sales_summary(date_from=date_from, date_to=date_to),
        "sales_by_day": sales_by_day(date_from=date_from, date_to=date_to),
        "sales_by_payment_method": sales_by_payment_method(date_from=date_from, date_to=date_to),
        "top_products": top_products(date_from=date_from, date_to=date_to),
        "gross_margin": gross_margin(date_from=date_from, date_to=date_to),
        "low_stock": low_stock_alerts(),
        "expiring_lots": expiring_lots(),
        "expired_lots": expired_lots(),
        "inventory": inventory_value(),
        "generated_at": timezone.now().isoformat(),
    }

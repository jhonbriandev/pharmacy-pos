"""API del catalogo.

El endpoint ``products/lookup`` es el que usa el punto de venta al escanear: en
una sola llamada devuelve precio, stock disponible y lotes en orden FEFO.
"""

from django.db.models import F, Prefetch, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsCatalogEditor
from apps.catalog.models import (
    ActiveIngredient,
    Category,
    Laboratory,
    Product,
    ProductGroup,
    UnitConversion,
)
from apps.catalog.serializers import (
    ActiveIngredientSerializer,
    CategorySerializer,
    LaboratorySerializer,
    LotSummarySerializer,
    ProductGroupSerializer,
    ProductLookupSerializer,
    ProductSerializer,
    UnitConversionSerializer,
)
from apps.inventory.models import Lot
from apps.inventory.services import is_expired, today


def sellable_lots_prefetch() -> Prefetch:
    """Trae en una sola consulta los lotes vendibles, en orden FEFO.

    Se usa ``to_attr`` para que el serializer no tenga que volver a consultar
    la base de datos por cada producto.
    """
    return Prefetch(
        "lots",
        queryset=Lot.objects.filter(
            is_blocked=False,
            current_quantity__gt=0,
            expiry_date__gte=today(),
        ).order_by("expiry_date", "id"),
        to_attr="available_lots",
    )


class LaboratoryViewSet(ModelViewSet):
    queryset = Laboratory.objects.all()
    serializer_class = LaboratorySerializer
    permission_classes = [IsCatalogEditor]
    search_fields = ("name",)
    filterset_fields = ("is_active",)
    ordering_fields = ("name",)


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsCatalogEditor]
    search_fields = ("name",)
    filterset_fields = ("is_active",)
    ordering_fields = ("name",)


class ActiveIngredientViewSet(ModelViewSet):
    queryset = ActiveIngredient.objects.all()
    serializer_class = ActiveIngredientSerializer
    permission_classes = [IsCatalogEditor]
    search_fields = ("name",)
    filterset_fields = ("is_active",)
    ordering_fields = ("name",)


class ProductGroupViewSet(ModelViewSet):
    queryset = ProductGroup.objects.select_related("laboratory", "category").prefetch_related(
        "ingredients", "products"
    )
    serializer_class = ProductGroupSerializer
    permission_classes = [IsCatalogEditor]
    search_fields = ("name", "concentration", "laboratory__name")
    filterset_fields = ("is_active", "pharmaceutical_form", "laboratory", "category")
    ordering_fields = ("name", "concentration")


class UnitConversionViewSet(ModelViewSet):
    queryset = UnitConversion.objects.select_related("group", "source", "target").order_by("id")
    serializer_class = UnitConversionSerializer
    permission_classes = [IsCatalogEditor]
    filterset_fields = ("group", "source", "target")


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsCatalogEditor]
    search_fields = ("group__name", "group__concentration", "barcode", "presentation_detail")
    filterset_fields = ("is_active", "presentation", "group", "group__laboratory")
    ordering_fields = ("group__name", "sale_price", "min_stock")

    def get_queryset(self):
        """Productos con su stock vendible anotado en SQL (sin consultas N+1)."""
        from apps.inventory.services import sellable_stock_expression

        return (
            Product.objects.select_related("group")
            .annotate(stock=sellable_stock_expression())
            .order_by("group__name", "presentation")
        )

    @action(detail=True, methods=["get"], url_path="lots")
    def lots(self, request, pk=None):
        """Lotes de un producto, incluidos los vencidos y los bloqueados."""
        product = self.get_object()
        lots = Lot.objects.filter(product=product).order_by("expiry_date", "id")
        data = [
            {
                "id": lot.pk,
                "batch_number": lot.batch_number,
                "expiry_date": lot.expiry_date,
                "current_quantity": lot.current_quantity,
                "cost_price": lot.cost_price,
                "is_blocked": lot.is_blocked,
                "block_reason": lot.block_reason,
                "is_expired": is_expired(lot),
            }
            for lot in lots
        ]
        return Response(LotSummarySerializer(data, many=True).data)

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        """Productos activos cuyo stock vendible esta por debajo del minimo."""
        products = (
            self.get_queryset()
            .filter(is_active=True, min_stock__gt=0)
            .filter(stock__lt=F("min_stock"))
            .order_by("stock", "group__name")
        )
        return Response(ProductSerializer(products, many=True).data)


class ProductLookupView(APIView):
    """Busqueda para el punto de venta: por codigo de barras o por texto."""

    permission_classes = [IsCatalogEditor]

    def get(self, request):
        barcode = request.query_params.get("barcode", "").strip()
        query = request.query_params.get("q", "").strip()

        if not barcode and not query:
            return Response(
                {
                    "error": {
                        "code": "missing_query",
                        "message": "Indica un codigo de barras o un texto de busqueda.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        base = Product.objects.select_related("group").prefetch_related(sellable_lots_prefetch())

        if barcode:
            product = base.filter(barcode=barcode, is_active=True).first()
            if product is None:
                raise NotFound("No existe un producto activo con ese codigo de barras.")
            product.stock = sum(lot.current_quantity for lot in product.available_lots)
            return Response(ProductLookupSerializer(product).data)

        products = base.filter(is_active=True).filter(
            Q(group__name__icontains=query)
            | Q(group__concentration__icontains=query)
            | Q(barcode__icontains=query)
        )[:20]

        results = []
        for product in products:
            product.stock = sum(lot.current_quantity for lot in product.available_lots)
            results.append(ProductLookupSerializer(product).data)
        return Response(results)

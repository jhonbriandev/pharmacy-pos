"""Serializers del catalogo."""

from rest_framework import serializers

from apps.catalog.models import (
    ActiveIngredient,
    Category,
    Laboratory,
    Product,
    ProductGroup,
    UnitConversion,
)


class LaboratorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Laboratory
        fields = ("id", "name", "is_active")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description", "is_active")


class ActiveIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveIngredient
        fields = ("id", "name", "is_active")


class ProductGroupSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    laboratory_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    ingredients = ActiveIngredientSerializer(many=True, read_only=True)
    ingredient_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ActiveIngredient.objects.all(),
        source="ingredients",
        write_only=True,
        required=False,
    )

    class Meta:
        model = ProductGroup
        fields = (
            "id",
            "name",
            "concentration",
            "pharmaceutical_form",
            "laboratory",
            "laboratory_name",
            "category",
            "category_name",
            "ingredients",
            "ingredient_ids",
            "notes",
            "is_active",
            "display_name",
        )

    def get_laboratory_name(self, obj: ProductGroup) -> str:
        return obj.laboratory.name if obj.laboratory_id else ""

    def get_category_name(self, obj: ProductGroup) -> str:
        return obj.category.name if obj.category_id else ""


class ProductSerializer(serializers.ModelSerializer):
    """Producto con costo y margen.

    El costo y el margen se exponen a todos los roles autenticados porque asi se
    aprobo en el proyecto (ver docs/decisiones.md, riesgo aceptado R-Q12). Lo que
    nunca ocurre es incluirlos en la boleta que ve el cliente.
    """

    display_name = serializers.CharField(read_only=True)
    group_name = serializers.SerializerMethodField()
    presentation_display = serializers.CharField(source="get_presentation_display", read_only=True)
    margin = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    stock = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Product
        fields = (
            "id",
            "group",
            "group_name",
            "display_name",
            "presentation",
            "presentation_display",
            "presentation_detail",
            "barcode",
            "unit_label",
            "sale_price",
            "tax_rate",
            "last_cost",
            "margin",
            "min_stock",
            "is_active",
            "stock",
        )
        read_only_fields = ("last_cost", "tax_rate")

    def get_group_name(self, obj: Product) -> str:
        return obj.group.name

    def validate_sale_price(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value

    def validate_barcode(self, value):
        """Un codigo vacio se guarda como NULL para no chocar con la unicidad."""
        return value or None


class LotSummarySerializer(serializers.Serializer):
    """Lote tal como se muestra en el detalle de un producto."""

    id = serializers.IntegerField()
    batch_number = serializers.CharField()
    expiry_date = serializers.DateField()
    current_quantity = serializers.IntegerField()
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=4)
    is_blocked = serializers.BooleanField()
    block_reason = serializers.CharField()
    is_expired = serializers.BooleanField()


class ProductLookupSerializer(serializers.ModelSerializer):
    """Respuesta del endpoint que usa el POS al escanear un producto."""

    display_name = serializers.CharField(read_only=True)
    presentation_display = serializers.CharField(source="get_presentation_display", read_only=True)
    stock = serializers.IntegerField(read_only=True, default=0)
    lots = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "display_name",
            "barcode",
            "presentation",
            "presentation_display",
            "sale_price",
            "tax_rate",
            "last_cost",
            "stock",
            "lots",
        )

    def get_lots(self, obj: Product):
        return [
            {
                "id": lot.pk,
                "batch_number": lot.batch_number,
                "expiry_date": lot.expiry_date.isoformat(),
                "quantity": lot.current_quantity,
            }
            for lot in getattr(obj, "available_lots", [])
        ]


class UnitConversionSerializer(serializers.ModelSerializer):
    source_label = serializers.CharField(source="source.display_name", read_only=True)
    target_label = serializers.CharField(source="target.display_name", read_only=True)

    class Meta:
        model = UnitConversion
        fields = ("id", "group", "source", "source_label", "target", "target_label", "factor")

    def validate(self, attrs):
        instance = UnitConversion(**attrs)
        instance.full_clean()
        return attrs

from django.contrib import admin

from apps.catalog.models import (
    ActiveIngredient,
    Category,
    Laboratory,
    Product,
    ProductGroup,
    UnitConversion,
)


@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(ActiveIngredient)
class ActiveIngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = (
        "presentation",
        "presentation_detail",
        "barcode",
        "sale_price",
        "min_stock",
        "is_active",
    )


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "concentration", "pharmaceutical_form", "laboratory", "is_active")
    list_filter = ("pharmaceutical_form", "laboratory", "is_active")
    search_fields = ("name", "concentration")
    filter_horizontal = ("ingredients",)
    inlines = [ProductInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "group",
        "presentation",
        "presentation_detail",
        "barcode",
        "sale_price",
        "min_stock",
        "is_active",
    )
    list_filter = ("presentation", "is_active", "group__laboratory")
    search_fields = ("barcode", "group__name", "group__concentration")
    list_select_related = ("group",)
    readonly_fields = ("last_cost",)


@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ("group", "source", "target", "factor")
    list_filter = ("group",)
    list_select_related = ("group", "source", "target")

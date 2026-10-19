"""Admin de ventas (solo lectura: las ventas no se editan)."""

from django.contrib import admin

from apps.sales.models import Payment, Sale, SaleItem, SaleItemLot, SaleNumberSequence


class SaleItemLotInline(admin.TabularInline):
    model = SaleItemLot
    extra = 0
    readonly_fields = ("lot", "quantity", "unit_cost")
    can_delete = False


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = ("product", "product_name", "quantity", "unit_price", "line_total", "unit_cost")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("method", "amount", "received_amount", "change_amount", "reference")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("number", "created_at", "created_by", "total", "status")
    list_filter = ("status", "created_at")
    search_fields = ("number", "created_by__username")
    list_select_related = ("created_by",)
    date_hierarchy = "created_at"
    inlines = [SaleItemInline, PaymentInline]
    readonly_fields = ("number", "total", "client_request_id", "created_by", "created_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(SaleNumberSequence)
class SaleNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ("id", "last_number")

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

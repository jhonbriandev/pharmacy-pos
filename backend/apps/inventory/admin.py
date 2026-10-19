"""Admin de inventario.

El libro mayor es inmutable: el admin solo lo muestra, nunca lo edita.
"""

from django.contrib import admin

from apps.inventory.models import Lot, StockEntry, StockEntryItem, StockMovement


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "batch_number",
        "expiry_date",
        "current_quantity",
        "cost_price",
        "is_blocked",
    )
    list_filter = ("is_blocked", "expiry_date")
    search_fields = ("batch_number", "product__barcode", "product__group__name")
    list_select_related = ("product", "product__group")
    readonly_fields = ("current_quantity",)
    date_hierarchy = "expiry_date"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "movement_type",
        "product",
        "lot",
        "quantity_delta",
        "balance_after",
        "created_by",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("lot__batch_number", "product__group__name", "reason")
    list_select_related = ("product", "lot", "created_by")
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class StockEntryItemInline(admin.TabularInline):
    model = StockEntryItem
    extra = 0
    fields = ("product", "lot", "quantity", "cost_price")
    readonly_fields = ("product", "lot", "quantity", "cost_price")

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("received_at", "supplier", "document_number", "created_by")
    list_filter = ("received_at",)
    search_fields = ("supplier", "document_number")
    date_hierarchy = "received_at"
    inlines = [StockEntryItemInline]

    def has_change_permission(self, request, obj=None) -> bool:
        # Las entradas ya registradas no se editan: se corrigen con un
        # movimiento inverso, dejando ambas huellas.
        return False

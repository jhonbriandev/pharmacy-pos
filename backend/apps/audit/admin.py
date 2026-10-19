"""Admin de auditoria: solo lectura, siempre."""

from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "entity_type", "entity_id", "ip_address")
    list_filter = ("action", "created_at")
    search_fields = ("entity_id", "actor__username")
    list_select_related = ("actor",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

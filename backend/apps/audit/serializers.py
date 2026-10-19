"""Serializers de auditoria (solo lectura)."""

from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    actor_name = serializers.SerializerMethodField()
    actor_username = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "created_at",
            "action",
            "action_display",
            "actor",
            "actor_name",
            "actor_username",
            "entity_type",
            "entity_id",
            "before",
            "after",
            "ip_address",
        )
        read_only_fields = fields

    def get_actor_name(self, obj: AuditEvent) -> str:
        return obj.actor.full_name if obj.actor_id else "Sistema"

    def get_actor_username(self, obj: AuditEvent) -> str:
        return obj.actor.username if obj.actor_id else ""

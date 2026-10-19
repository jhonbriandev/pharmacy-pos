"""Registro de auditoria inmutable.

Se implementa a mano en lugar de usar django-simple-history porque:
  - la version publica de simple-history no declara soporte para Django 6.x y
    aqui solo se necesitan acciones sensibles, no el historial de cada campo;
  - la inmutabilidad estricta (sin UPDATE ni DELETE) es un requisito del
    proyecto y conviene tenerla explicita y probada.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditAction(models.TextChoices):
    LOGIN_SUCCESS = "LOGIN_OK", "Inicio de sesion"
    LOGIN_FAILED = "LOGIN_FAIL", "Intento de sesion fallido"
    LOGOUT = "LOGOUT", "Cierre de sesion"
    PASSWORD_CHANGED = "PASSWORD_CHANGED", "Cambio de contrasena"
    PASSWORD_RESET = "PASSWORD_RESET", "Restablecimiento de contrasena"
    USER_CREATED = "USER_CREATED", "Usuario creado"
    USER_UPDATED = "USER_UPDATED", "Usuario actualizado"
    USER_DEACTIVATED = "USER_DEACTIVATED", "Usuario desactivado"
    ROLE_CHANGED = "ROLE_CHANGED", "Cambio de rol"
    PRODUCT_CREATED = "PRODUCT_CREATED", "Producto creado"
    PRODUCT_UPDATED = "PRODUCT_UPDATED", "Producto actualizado"
    PRICE_CHANGED = "PRICE_CHANGED", "Cambio de precio"
    STOCK_ENTRY_CREATED = "STOCK_ENTRY_CREATED", "Entrada de mercaderia"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT", "Ajuste de inventario"
    LOT_BLOCKED = "LOT_BLOCKED", "Lote bloqueado"
    FRACTIONATION = "FRACTIONATION", "Fraccionamiento de presentacion"
    SALE_CREATED = "SALE_CREATED", "Venta registrada"
    SALE_VOIDED = "SALE_VOIDED", "Venta anulada"


class AuditEvent(models.Model):
    """Evento de auditoria. No se modifica ni se elimina nunca."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        verbose_name="autor",
        null=True,
        blank=True,
    )
    action = models.CharField(
        "accion",
        max_length=40,
        choices=AuditAction.choices,
        db_index=True,
    )
    entity_type = models.CharField("tipo de entidad", max_length=80, blank=True)
    entity_id = models.CharField("id de entidad", max_length=64, blank=True)
    before = models.JSONField("estado anterior", null=True, blank=True)
    after = models.JSONField("estado posterior", null=True, blank=True)
    ip_address = models.GenericIPAddressField("direccion IP", null=True, blank=True)
    created_at = models.DateTimeField("creado el", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "evento de auditoria"
        verbose_name_plural = "eventos de auditoria"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"], name="idx_audit_entity"),
            models.Index(fields=["actor", "-created_at"], name="idx_audit_actor_date"),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} · {self.entity_type} {self.entity_id}".strip()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Los eventos de auditoria son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los eventos de auditoria no se pueden eliminar.")

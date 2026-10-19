"""Servicio de registro de auditoria.

Un unico punto de entrada para que todos los eventos tengan la misma forma y
para que sea imposible registrar datos sensibles por descuido.
"""

from __future__ import annotations

from typing import Any

from apps.audit.models import AuditEvent

SENSITIVE_KEY_FRAGMENTS = ("password", "contrasena", "token", "secret", "clave")


def _sanitize(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Elimina cualquier clave que parezca contener un secreto."""
    if not data:
        return data
    clean: dict[str, Any] = {}
    for key, value in data.items():
        if any(fragment in key.lower() for fragment in SENSITIVE_KEY_FRAGMENTS):
            clean[key] = "***"
        elif isinstance(value, dict):
            clean[key] = _sanitize(value)
        else:
            clean[key] = value
    return clean


def get_client_ip(request) -> str | None:
    """Obtiene la IP real detras del proxy de Render/Vercel."""
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record_event(
    *,
    action: str,
    entity=None,
    actor=None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request=None,
) -> AuditEvent:
    """Registra un evento de auditoria.

    ``entity`` puede ser una instancia de modelo (se guardan su tipo y su pk) o
    ``None`` para eventos sin entidad (por ejemplo, un inicio de sesion).
    """
    entity_type = ""
    entity_id = ""
    if entity is not None:
        entity_type = entity._meta.label
        entity_id = str(getattr(entity, "pk", "") or "")

    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=_sanitize(before),
        after=_sanitize(after),
        ip_address=get_client_ip(request),
    )

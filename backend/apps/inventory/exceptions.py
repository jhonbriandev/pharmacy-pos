"""Errores de dominio de inventario.

Heredan de ``BusinessError`` (HTTP 409): la peticion esta bien formada, pero el
estado actual del inventario no permite completarla.
"""

from apps.common.exceptions import BusinessError


class InsufficientStock(BusinessError):
    default_code = "insufficient_stock"
    default_detail = "No hay stock suficiente para completar la operacion."


class LotExpired(BusinessError):
    default_code = "lot_expired"
    default_detail = "El lote esta vencido y no puede venderse."


class LotBlocked(BusinessError):
    default_code = "lot_blocked"
    default_detail = "El lote esta bloqueado y no puede utilizarse."


class InvalidConversion(BusinessError):
    default_code = "invalid_conversion"
    default_detail = "No existe una conversion valida entre esas presentaciones."


class LotExpiryMismatch(BusinessError):
    default_code = "lot_expiry_mismatch"
    default_detail = (
        "El lote ya existe con otra fecha de vencimiento. "
        "Verifica el numero de lote antes de continuar."
    )

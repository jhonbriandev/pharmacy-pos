"""Errores de dominio de ventas."""

from apps.common.exceptions import BusinessError


class ProductNotAvailable(BusinessError):
    default_code = "product_not_available"
    default_detail = "Hay productos que no existen o estan inactivos."


class InsufficientPayment(BusinessError):
    default_code = "insufficient_payment"
    default_detail = "El monto recibido es menor que el total de la venta."


class PaymentMismatch(BusinessError):
    default_code = "payment_mismatch"
    default_detail = "El monto del pago no coincide con el total de la venta."

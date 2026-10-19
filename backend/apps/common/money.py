"""Aritmetica de dinero.

Todo importe monetario del sistema pasa por aqui: se trabaja con ``Decimal`` y
se redondea con ``ROUND_HALF_UP`` (el criterio comercial habitual en Peru),
nunca con el redondeo bancario por defecto de Python ni con ``float``.
"""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
UNIT_COST = Decimal("0.0001")
ZERO = Decimal("0.00")


def money(value: Decimal | int | str) -> Decimal:
    """Redondea un importe a 2 decimales (soles)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def unit_cost(value: Decimal | int | str) -> Decimal:
    """Redondea un costo unitario a 4 decimales.

    Los costos por unidad pueden venir de dividir el costo de una caja entre
    sus unidades, por lo que se necesitan mas decimales que en el precio.
    """
    return Decimal(value).quantize(UNIT_COST, rounding=ROUND_HALF_UP)

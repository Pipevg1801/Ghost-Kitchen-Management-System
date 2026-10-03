from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def moneda(valor):
    """Formato de pesos colombianos: 12345.5 -> "$12.345,50"; 12345 -> "$12.345"."""
    try:
        valor = Decimal(valor).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return "$0"
    entero, decimales = f"{abs(valor):,.2f}".split(".")
    signo = "-" if valor < 0 else ""
    entero = entero.replace(",", ".")
    return f"{signo}${entero}" if decimales == "00" else f"{signo}${entero},{decimales}"

from django import template

from orders.models import Pedido

register = template.Library()

Estado = Pedido.Estado

ICONOS_ESTADO = {
    Estado.RECIBIDO: "bi-inbox",
    Estado.EN_PREPARACION: "bi-fire",
    Estado.LISTO: "bi-check-circle-fill",
    Estado.CANCELADO: "bi-x-circle",
}
PASOS_FLUJO = (Estado.RECIBIDO, Estado.EN_PREPARACION, Estado.LISTO)


@register.inclusion_tag("orders/includes/badge_estado.html")
def badge_estado(pedido):
    return {
        "estado": pedido.estado,
        "etiqueta": pedido.get_estado_display(),
        "icono": ICONOS_ESTADO.get(pedido.estado, "bi-circle"),
    }


@register.inclusion_tag("orders/includes/progreso.html")
def progreso_pedido(pedido):
    cancelado = pedido.estado == Estado.CANCELADO
    indice_actual = PASOS_FLUJO.index(pedido.estado) if pedido.estado in PASOS_FLUJO else -1
    pasos = [
        {
            "etiqueta": Estado(paso).label,
            "icono": ICONOS_ESTADO[paso],
            "completado": not cancelado and i <= indice_actual,
            "actual": not cancelado and i == indice_actual,
        }
        for i, paso in enumerate(PASOS_FLUJO)
    ]
    return {"pasos": pasos, "cancelado": cancelado}

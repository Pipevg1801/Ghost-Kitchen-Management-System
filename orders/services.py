"""Reglas de negocio de pedidos e inventario.

Todas las operaciones se ejecutan en una transacción y bloquean las filas
afectadas (SELECT ... FOR UPDATE) para evitar condiciones de carrera.

Inventario:
  confirmar -> disponible -= n, reservada += n
  listo     -> reservada  -= n                  (el plato se consumió)
  cancelar  -> disponible += n, reservada -= n  (se devuelve al menú)
"""
from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest

from menu.models import Plato

from .models import Pedido, PedidoDetalle

Estado = Pedido.Estado


class ErrorPedido(Exception):
    pass


class DisponibilidadInsuficiente(ErrorPedido):
    pass


class TransicionInvalida(ErrorPedido):
    pass


class PedidoNoCancelable(ErrorPedido):
    pass


@transaction.atomic
def confirmar_pedido(usuario, cantidades):
    """Convierte {id_plato: cantidad} en un Pedido con sus detalles."""
    if not cantidades:
        raise ErrorPedido("El carrito está vacío: agregue al menos un producto.")
    if any(cantidad <= 0 for cantidad in cantidades.values()):
        raise ErrorPedido("Las cantidades deben ser mayores que cero.")

    platos = {
        plato.pk: plato
        for plato in Plato.objects.select_for_update().filter(pk__in=cantidades).order_by("pk")
    }
    faltantes = []
    for plato_id, cantidad in cantidades.items():
        plato = platos.get(plato_id)
        if plato is None or not plato.activo:
            raise ErrorPedido("Uno de los productos del carrito ya no está disponible.")
        if cantidad > plato.cantidad_disponible:
            faltantes.append(f"{plato.nombre} (disponibles: {plato.cantidad_disponible})")
    if faltantes:
        raise DisponibilidadInsuficiente(
            "No hay suficiente disponibilidad: " + ", ".join(faltantes) + "."
        )

    pedido = Pedido.objects.create(usuario=usuario, estado=Estado.RECIBIDO)
    detalles = []
    for plato_id, cantidad in sorted(cantidades.items()):
        plato = platos[plato_id]
        Plato.objects.filter(pk=plato_id).update(
            cantidad_disponible=F("cantidad_disponible") - cantidad,
            cantidad_reservada=F("cantidad_reservada") + cantidad,
        )
        detalles.append(PedidoDetalle(
            pedido=pedido, plato=plato, cantidad=cantidad, precio_unitario=plato.precio,
        ))
    PedidoDetalle.objects.bulk_create(detalles)

    pedido.total = pedido.calcular_total()
    pedido.save(update_fields=["total"])
    return pedido


def _liberar_reservas(pedido, devolver_disponible):
    for detalle in pedido.detalles.all():
        cambios = {
            "cantidad_reservada": Greatest(F("cantidad_reservada") - detalle.cantidad, Value(0)),
        }
        if devolver_disponible:
            cambios["cantidad_disponible"] = F("cantidad_disponible") + detalle.cantidad
        Plato.objects.filter(pk=detalle.plato_id).update(**cambios)


@transaction.atomic
def cambiar_estado(pedido_id, nuevo_estado):
    """Avanza un pedido al siguiente estado del flujo. Rechaza saltos o retrocesos."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido_id)
    if not pedido.puede_transicionar_a(nuevo_estado):
        destino = dict(Estado.choices).get(nuevo_estado, nuevo_estado)
        raise TransicionInvalida(
            f"El pedido #{pedido.pk} no puede pasar de «{pedido.get_estado_display()}» a «{destino}»."
        )
    if nuevo_estado == Estado.LISTO:
        _liberar_reservas(pedido, devolver_disponible=False)
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    return pedido


@transaction.atomic
def cancelar_pedido(pedido_id, usuario):
    """Cancela un pedido propio en estado Recibido y devuelve el inventario."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido_id, usuario=usuario)
    if not pedido.puede_cancelarse:
        raise PedidoNoCancelable(
            "Solo se pueden cancelar pedidos en estado «Recibido»; "
            "este pedido ya está en cocina."
        )
    _liberar_reservas(pedido, devolver_disponible=True)
    pedido.estado = Estado.CANCELADO
    pedido.save(update_fields=["estado"])
    return pedido

"""Datos de informes: pedidos paginados, agregados e inventario actual."""

from django.db.models import Count, Prefetch, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from menu.models import Categoria, Plato
from orders.models import Pedido, PedidoDetalle

from . import services

ESTADOS = Pedido.Estado


def serie_diaria(pedidos):
    filas = (
        pedidos.annotate(fecha=TruncDate("fecha_creacion"))
        .values("fecha", "estado")
        .annotate(cantidad=Count("id"), total=Sum("total"))
        .order_by("fecha", "estado")
    )
    dias = {}
    for fila in filas:
        fecha, estado = fila["fecha"], fila["estado"]
        dia = dias.setdefault(fecha, {
            "fecha": fecha,
            "por_estado": dict.fromkeys(ESTADOS.values, 0),
            "ingresos": services.CERO,
        })
        dia["por_estado"][estado] = fila["cantidad"]
        if estado != ESTADOS.CANCELADO:
            dia["ingresos"] += fila["total"]
    return list(dias.values())


def inventario_actual():
    categorias = Categoria.objects.values(
        "id", "nombre", "slug", "descripcion", "orden", "activa",
    )
    platos = Plato.objects.only(
        "id", "nombre", "descripcion", "categoria", "precio", "imagen",
        "cantidad_disponible", "cantidad_reservada", "activo",
    )
    return {
        "categorias": list(categorias),
        "platos": [
            {
                "id": plato.pk,
                "nombre": plato.nombre,
                "descripcion": plato.descripcion,
                "categoria_id": plato.categoria_id,
                "precio": plato.precio,
                "imagen_url": plato.imagen.url if plato.imagen else None,
                "cantidad_disponible": plato.cantidad_disponible,
                "cantidad_reservada": plato.cantidad_reservada,
                "activo": plato.activo,
            }
            for plato in platos
        ],
    }


def preparar_pedidos(pedidos):
    detalles = PedidoDetalle.objects.select_related("plato").only(
        "id", "pedido", "plato", "plato__nombre", "cantidad", "precio_unitario",
    )
    return (
        pedidos.only("id", "fecha_creacion", "estado", "total", "usuario", "usuario__nombre")
        .prefetch_related(Prefetch("detalles", queryset=detalles))
        .order_by("-fecha_creacion", "-id")
    )


def serializar_pedido(pedido):
    return {
        "id": pedido.pk,
        "fecha_creacion": timezone.localtime(pedido.fecha_creacion).isoformat(),
        "estado": pedido.estado,
        "cliente": {"id": pedido.usuario_id, "nombre": pedido.usuario.nombre},
        "total": pedido.total,
        "detalles": [
            {
                "id": detalle.pk,
                "plato_id": detalle.plato_id,
                "plato_nombre": detalle.plato.nombre,
                "cantidad": detalle.cantidad,
                "precio_unitario": detalle.precio_unitario,
                "subtotal": detalle.subtotal,
            }
            for detalle in pedido.detalles.all()
        ],
    }


def agregados(pedidos):
    resumen = services.resumen_de(pedidos)
    resumen["pedidos_totales"] = resumen["pedidos"] + resumen["cancelados"]
    return {
        "resumen": resumen,
        "por_estado": services.conteos_por_estado(pedidos),
        "serie_diaria": serie_diaria(pedidos),
        "platos_mas_vendidos": [
            {
                "plato_id": fila["plato_id"],
                "nombre": fila["plato__nombre"],
                "categoria_id": fila["plato__categoria_id"],
                "unidades": fila["unidades"],
                "ingresos": fila["ingresos"],
            }
            for fila in services.ventas_por_plato(pedidos)
        ],
    }

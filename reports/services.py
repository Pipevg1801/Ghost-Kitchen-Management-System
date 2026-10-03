"""Consultas agregadas de informes, calculadas en la base de datos con el ORM.

Regla de negocio: los pedidos CANCELADOS no cuentan como ventas. «Pedidos»,
«Ingresos» y «Ticket promedio» usan solo pedidos no cancelados.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from orders.models import Pedido, PedidoDetalle

Estado = Pedido.Estado
CERO = Decimal("0.00")
DINERO = DecimalField(max_digits=14, decimal_places=2)

PERIODOS = {
    "hoy": ("Hoy", 1),
    "7d": ("Últimos 7 días", 7),
    "30d": ("Últimos 30 días", 30),
    "todo": ("Histórico", None),
}
DIAS_GRAFICO = (7, 14, 30)


def pedidos_del_periodo(periodo):
    _, dias = PERIODOS.get(periodo, PERIODOS["hoy"])
    pedidos = Pedido.objects.all()
    if dias:
        desde = timezone.localdate() - timedelta(days=dias - 1)
        pedidos = pedidos.filter(fecha_creacion__date__gte=desde)
    return pedidos


def resumen_consolidado(periodo="hoy"):
    pedidos = pedidos_del_periodo(periodo)
    no_cancelado = ~Q(estado=Estado.CANCELADO)
    datos = pedidos.aggregate(
        pedidos=Count("id", filter=no_cancelado),
        ingresos=Coalesce(Sum("total", filter=no_cancelado), Value(CERO), output_field=DINERO),
        cancelados=Count("id", filter=Q(estado=Estado.CANCELADO)),
        activos=Count("id", filter=Q(estado__in=Pedido.ESTADOS_ACTIVOS)),
        listos=Count("id", filter=Q(estado=Estado.LISTO)),
    )
    datos["ticket_promedio"] = (
        (datos["ingresos"] / datos["pedidos"]).quantize(Decimal("0.01"))
        if datos["pedidos"] else CERO
    )
    datos["periodo"] = periodo if periodo in PERIODOS else "hoy"
    datos["periodo_etiqueta"] = PERIODOS[datos["periodo"]][0]
    return datos


def pedidos_por_estado(periodo="hoy"):
    conteos = dict(
        pedidos_del_periodo(periodo).order_by().values_list("estado").annotate(n=Count("id"))
    )
    return [
        {"estado": valor, "etiqueta": etiqueta, "cantidad": conteos.get(valor, 0)}
        for valor, etiqueta in Estado.choices
    ]


def platos_mas_vendidos(periodo="hoy", limite=5):
    subtotal = ExpressionWrapper(F("cantidad") * F("precio_unitario"), output_field=DINERO)
    return list(
        PedidoDetalle.objects
        .filter(pedido__in=pedidos_del_periodo(periodo).exclude(estado=Estado.CANCELADO))
        .values("plato__nombre")
        .annotate(unidades=Sum("cantidad"), ingresos=Sum(subtotal))
        .order_by("-unidades", "plato__nombre")[:limite]
    )


def datos_grafico(dias=7):
    """Series diarias por estado e ingresos diarios de los últimos `dias` días."""
    dias = dias if dias in DIAS_GRAFICO else DIAS_GRAFICO[0]
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=dias - 1)
    fechas = [desde + timedelta(days=i) for i in range(dias)]

    pedidos = Pedido.objects.filter(fecha_creacion__date__gte=desde).annotate(dia=TruncDate("fecha_creacion"))
    series = {valor: [0] * dias for valor in Estado.values}
    for fila in pedidos.order_by().values("dia", "estado").annotate(n=Count("id")):
        series[fila["estado"]][(fila["dia"] - desde).days] = fila["n"]

    ingresos = [0.0] * dias
    filas_ingresos = (
        pedidos.exclude(estado=Estado.CANCELADO).order_by().values("dia")
        .annotate(total=Sum("total"))
    )
    for fila in filas_ingresos:
        ingresos[(fila["dia"] - desde).days] = float(fila["total"] or 0)

    return {
        "dias": dias,
        "etiquetas": [fecha.strftime("%d/%m") for fecha in fechas],
        "series": [
            {"estado": valor, "etiqueta": etiqueta, "datos": series[valor]}
            for valor, etiqueta in Estado.choices
        ],
        "ingresos": ingresos,
        "totales_por_estado": {valor: sum(series[valor]) for valor in Estado.values},
    }


def filtrar_pedidos(estado=None, desde=None, hasta=None, cliente=None):
    pedidos = Pedido.objects.select_related("usuario").order_by("-fecha_creacion")
    if estado:
        pedidos = pedidos.filter(estado=estado)
    if desde:
        pedidos = pedidos.filter(fecha_creacion__date__gte=desde)
    if hasta:
        pedidos = pedidos.filter(fecha_creacion__date__lte=hasta)
    if cliente:
        pedidos = pedidos.filter(Q(usuario__nombre__icontains=cliente) | Q(usuario__email__icontains=cliente))
    return pedidos


def totales_de(pedidos):
    return pedidos.aggregate(
        cantidad=Count("id"),
        suma=Coalesce(Sum("total"), Value(CERO), output_field=DINERO),
    )

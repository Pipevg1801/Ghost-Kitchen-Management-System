from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import Rol
from accounts.permissions import cliente_requerido, operario_requerido, rol_requerido
from core.http import destino_seguro, es_ajax, responder_accion
from menu.models import Plato

from . import services
from .cart import Carrito, ErrorCarrito
from .forms import AgregarCarritoForm, CambiarEstadoForm, EliminarDelCarritoForm, ModificarCarritoForm
from .models import Pedido

Estado = Pedido.Estado


# --- Carrito ---------------------------------------------------------------

def _datos_carrito(request, carrito):
    """Fragmentos HTML y contadores para refrescar el carrito sin recargar."""
    resumen = carrito.resumen()
    contexto = {"carrito": resumen}
    return {"carrito": {
        "cantidad": resumen["cantidad"],
        "por_plato": {item.plato.pk: item.cantidad for item in resumen["items"]},
        "html_compacto": render_to_string("orders/includes/carrito_compacto.html", contexto, request),
        "html_completo": render_to_string("orders/includes/carrito_completo.html", contexto, request),
    }}


def _responder_carrito(request, carrito, mensaje, ok=True, nivel=None):
    destino = destino_seguro(request, reverse("orders:carrito"))
    return responder_accion(
        request, mensaje, destino, ok=ok, nivel=nivel,
        datos=_datos_carrito(request, carrito) if es_ajax(request) else None,
    )


@cliente_requerido
@require_GET
def carrito(request):
    return render(request, "orders/carrito.html", {"carrito": Carrito(request).resumen()})


@cliente_requerido
@require_POST
def carrito_agregar(request):
    carrito = Carrito(request)
    form = AgregarCarritoForm(request.POST)
    if not form.is_valid():
        return _responder_carrito(request, carrito, "Cantidad no válida.", ok=False)
    plato = get_object_or_404(Plato, pk=form.cleaned_data["plato_id"])
    try:
        carrito.agregar(plato, form.cleaned_data["cantidad"])
    except ErrorCarrito as error:
        return _responder_carrito(request, carrito, str(error), ok=False)
    return _responder_carrito(request, carrito, f"{plato.nombre}: producto agregado al carrito.")


@cliente_requerido
@require_POST
def carrito_modificar(request):
    carrito = Carrito(request)
    form = ModificarCarritoForm(request.POST)
    if not form.is_valid():
        return _responder_carrito(request, carrito, "Acción no válida.", ok=False)
    plato = get_object_or_404(Plato, pk=form.cleaned_data["plato_id"])
    try:
        if form.cleaned_data["accion"] == ModificarCarritoForm.INCREMENTAR:
            carrito.incrementar(plato)
        else:
            carrito.disminuir(plato)
    except ErrorCarrito as error:
        return _responder_carrito(request, carrito, str(error), ok=False)
    return _responder_carrito(request, carrito, "Carrito actualizado.")


@cliente_requerido
@require_POST
def carrito_eliminar(request):
    carrito = Carrito(request)
    form = EliminarDelCarritoForm(request.POST)
    if not form.is_valid():
        return _responder_carrito(request, carrito, "Producto no válido.", ok=False)
    plato = get_object_or_404(Plato, pk=form.cleaned_data["plato_id"])
    carrito.eliminar(plato)
    return _responder_carrito(request, carrito, "Producto eliminado del carrito.", nivel="info")


@cliente_requerido
@require_POST
def carrito_cancelar(request):
    carrito = Carrito(request)
    carrito.vaciar()
    return _responder_carrito(request, carrito, "Carrito cancelado.", nivel="info")


@cliente_requerido
@require_POST
def pedido_confirmar(request):
    carrito = Carrito(request)
    try:
        pedido = services.confirmar_pedido(request.user, carrito.cantidades())
    except services.ErrorPedido as error:
        return responder_accion(request, str(error), reverse("orders:carrito"), ok=False)
    carrito.vaciar()
    return responder_accion(
        request, f"Pedido #{pedido.pk} creado correctamente.",
        reverse("orders:pedido_detalle", args=[pedido.pk]),
    )


# --- Pedidos del cliente ---------------------------------------------------

@cliente_requerido
@require_GET
def mis_pedidos(request):
    pedidos = Pedido.objects.del_usuario(request.user).con_detalles()
    pagina = Paginator(pedidos, 8).get_page(request.GET.get("page"))
    contexto = {"pagina": pagina, "pedidos": pagina.object_list}
    plantilla = "orders/includes/lista_mis_pedidos.html" if es_ajax(request) else "orders/mis_pedidos.html"
    return render(request, plantilla, contexto)


@rol_requerido(Rol.Nombre.CLIENTE, Rol.Nombre.OPERARIO, Rol.Nombre.ADMINISTRADOR)
@require_GET
def pedido_detalle(request, pk):
    pedidos = Pedido.objects.con_detalles()
    if request.user.es_cliente:
        pedidos = pedidos.del_usuario(request.user)
    pedido = get_object_or_404(pedidos, pk=pk)
    return render(request, "orders/pedido_detalle.html", {"pedido": pedido})


@cliente_requerido
@require_POST
def pedido_cancelar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, usuario=request.user)
    destino = destino_seguro(request, reverse("orders:pedido_detalle", args=[pedido.pk]))
    try:
        services.cancelar_pedido(pedido.pk, request.user)
    except services.PedidoNoCancelable as error:
        return responder_accion(request, str(error), destino, ok=False)
    return responder_accion(request, f"Pedido #{pedido.pk} cancelado.", destino,
                            nivel="info", datos={"refrescar": True})


# --- Panel del operario ----------------------------------------------------

@operario_requerido
@require_GET
def operario_pedidos(request):
    activos = list(Pedido.objects.activos().con_detalles().order_by("fecha_creacion"))
    listos = (
        Pedido.objects.filter(estado=Estado.LISTO, fecha_creacion__date=timezone.localdate())
        .con_detalles().order_by("-fecha_creacion")[:12]
    )
    contexto = {
        "pedidos_activos": activos,
        "pedidos_listos": listos,
        "total_recibidos": sum(1 for p in activos if p.estado == Estado.RECIBIDO),
        "total_en_preparacion": sum(1 for p in activos if p.estado == Estado.EN_PREPARACION),
    }
    plantilla = "orders/operario/_tablero.html" if es_ajax(request) else "orders/operario/pedidos.html"
    return render(request, plantilla, contexto)


@operario_requerido
@require_POST
def operario_cambiar_estado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    destino = reverse("orders:operario_pedidos")
    form = CambiarEstadoForm(request.POST)
    if not form.is_valid():
        return responder_accion(request, "Estado no válido.", destino, ok=False)
    try:
        pedido = services.cambiar_estado(pedido.pk, form.cleaned_data["estado"])
    except services.TransicionInvalida as error:
        return responder_accion(request, str(error), destino, ok=False, datos={"refrescar": True})
    return responder_accion(
        request,
        f"Estado del pedido actualizado: #{pedido.pk} → {pedido.get_estado_display()}.",
        destino, datos={"refrescar": True},
    )

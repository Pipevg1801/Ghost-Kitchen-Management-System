from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, ListView, UpdateView

from accounts.models import Rol
from accounts.permissions import AdministradorRequeridoMixin, administrador_requerido, rol_requerido
from orders.cart import Carrito

from .forms import PlatoForm
from .models import Plato

def _ordenar_por_categoria(queryset):
    """Ordena los platos para que las categorías queden contiguas."""
    return queryset.select_related("categoria").order_by(
        "categoria__orden", "categoria__nombre", "nombre"
    )


def _filtrar_por_busqueda(queryset, termino):
    termino = (termino or "").strip()
    if termino:
        queryset = queryset.filter(Q(nombre__icontains=termino) | Q(descripcion__icontains=termino))
    return queryset, termino


@rol_requerido(Rol.Nombre.CLIENTE, Rol.Nombre.OPERARIO)
@require_GET
def catalogo(request):
    platos, busqueda = _filtrar_por_busqueda(
        _ordenar_por_categoria(Plato.objects.activos()),
        request.GET.get("q"),
    )
    contexto = {"platos": platos, "busqueda": busqueda}
    if request.user.es_cliente:
        carrito = Carrito(request)
        en_carrito = carrito.cantidades()
        platos = list(platos)
        for plato in platos:
            plato.en_carrito = en_carrito.get(plato.pk, 0)
        contexto.update(platos=platos, carrito=carrito.resumen())
    return render(request, "menu/catalogo.html", contexto)


# --- Gestión del menú (Administrador) --------------------------------------

class PlatoListaView(AdministradorRequeridoMixin, ListView):
    model = Plato
    template_name = "menu/admin_lista.html"
    context_object_name = "platos"
    paginate_by = 15

    def get_queryset(self):
        queryset, self.busqueda = _filtrar_por_busqueda(
            Plato.objects.order_by("-activo", "nombre"), self.request.GET.get("q")
        )
        return queryset

    def get_context_data(self, **kwargs):
        return super().get_context_data(busqueda=self.busqueda, **kwargs)


class PlatoCrearView(AdministradorRequeridoMixin, SuccessMessageMixin, CreateView):
    model = Plato
    form_class = PlatoForm
    template_name = "menu/plato_form.html"
    success_url = reverse_lazy("menu:admin_lista")
    success_message = "Producto creado correctamente."
    extra_context = {"titulo": "Agregar producto", "boton": "Crear producto"}


class PlatoEditarView(AdministradorRequeridoMixin, SuccessMessageMixin, UpdateView):
    model = Plato
    form_class = PlatoForm
    template_name = "menu/plato_form.html"
    success_url = reverse_lazy("menu:admin_lista")
    success_message = "Producto actualizado."
    extra_context = {"titulo": "Modificar producto", "boton": "Guardar cambios"}


@administrador_requerido
@require_POST
def plato_eliminar(request, pk):
    plato = get_object_or_404(Plato, pk=pk)
    if plato.detalles.exists():
        # Conserva el historial: los pedidos antiguos siguen apuntando al plato.
        plato.activo = False
        plato.save(update_fields=["activo"])
        messages.warning(
            request,
            f"Producto eliminado del menú: «{plato.nombre}» tiene pedidos asociados, "
            "por lo que se ocultó y se conserva en el historial.",
        )
    else:
        nombre = plato.nombre
        plato.delete()
        messages.success(request, f"Producto eliminado: «{nombre}».")
    return redirect("menu:admin_lista")

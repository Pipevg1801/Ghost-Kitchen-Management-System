from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from accounts.permissions import administrador_requerido
from menu.models import Plato
from orders.models import Pedido

from . import services
from .forms import FiltroPedidosForm, PeriodoForm

UMBRAL_POCA_DISPONIBILIDAD = 3


def _periodo(request):
    form = PeriodoForm(request.GET)
    return form, form.periodo_elegido()


@administrador_requerido
@require_GET
def dashboard(request):
    contexto = {
        "resumen": services.resumen_consolidado("hoy"),
        "pedidos_recientes": Pedido.objects.select_related("usuario")[:8],
        "platos_poca_disponibilidad": Plato.objects.activos().filter(
            cantidad_disponible__lte=UMBRAL_POCA_DISPONIBILIDAD
        ).order_by("cantidad_disponible", "nombre"),
        "total_platos": Plato.objects.activos().count(),
    }
    return render(request, "reports/dashboard.html", contexto)


@administrador_requerido
@require_GET
def informes(request):
    form, periodo = _periodo(request)
    contexto = {
        "form": form,
        "resumen": services.resumen_consolidado(periodo),
        "pedidos": Pedido.objects.select_related("usuario")[:10],
        "dias_grafico": services.DIAS_GRAFICO,
    }
    return render(request, "reports/informes.html", contexto)


@administrador_requerido
@require_GET
def consolidado(request):
    form, periodo = _periodo(request)
    contexto = {
        "form": form,
        "resumen": services.resumen_consolidado(periodo),
        "por_estado": services.pedidos_por_estado(periodo),
        "mas_vendidos": services.platos_mas_vendidos(periodo),
    }
    return render(request, "reports/consolidado.html", contexto)


@administrador_requerido
@require_GET
def grafico(request):
    return render(request, "reports/grafico.html", {"dias_grafico": services.DIAS_GRAFICO})


@administrador_requerido
@require_GET
def grafico_datos(request):
    try:
        dias = int(request.GET.get("dias", services.DIAS_GRAFICO[0]))
    except ValueError:
        dias = services.DIAS_GRAFICO[0]
    return JsonResponse(services.datos_grafico(dias))


@administrador_requerido
@require_GET
def tabular(request):
    form = FiltroPedidosForm(request.GET or None)
    pedidos = services.filtrar_pedidos(**form.filtros())
    pagina = Paginator(pedidos, 15).get_page(request.GET.get("page"))
    contexto = {
        "form": form,
        "pagina": pagina,
        "pedidos": pagina.object_list,
        "totales": services.totales_de(pedidos),
    }
    return render(request, "reports/tabular.html", contexto)

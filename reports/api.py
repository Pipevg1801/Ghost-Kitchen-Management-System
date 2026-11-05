"""API versionada de informes; no permite mutaciones."""

from secrets import compare_digest

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.vary import vary_on_headers

from . import export, services
from .forms import FiltrosInformeAPIForm


def _error(codigo, mensaje, status, *, headers=None, campos=None):
    error = {"codigo": codigo, "mensaje": mensaje}
    if campos is not None:
        error["campos"] = campos
    return JsonResponse({"error": error}, status=status, headers=headers)


def _validar_acceso(request):
    autorizacion = request.headers.get("Authorization")
    if autorizacion is not None:
        esquema, _, token = autorizacion.partition(" ")
        esperado = settings.REPORTS_API_TOKEN
        if esquema.lower() == "bearer" and esperado and compare_digest(
            token.encode("utf-8"), esperado.encode("utf-8")
        ):
            return None
    elif request.user.is_authenticated:
        if request.user.es_administrador:
            return None
        return _error("sin_permiso", "Se requiere el rol Administrador.", 403)
    return _error(
        "no_autenticado", "Inicia sesión como administrador o usa un token de informes válido.",
        401, headers={"WWW-Authenticate": 'Bearer realm="informes"'},
    )


# Sin escritura: los métodos distintos de GET devuelven un 405 JSON antes de autenticar.
@csrf_exempt
@never_cache
@vary_on_headers("Authorization", "Cookie")
def informe(request):
    if request.method != "GET":
        return _error("metodo_no_permitido", "Usa GET.", 405, headers={"Allow": "GET"})
    error = _validar_acceso(request)
    if error is not None:
        return error

    formulario = FiltrosInformeAPIForm(request.GET)
    if not formulario.is_valid():
        return _error(
            "filtros_invalidos", "Revisa los parámetros de consulta.", 400,
            campos=formulario.errors.get_json_data(),
        )

    filtros = formulario.filtros()
    numero = filtros.pop("pagina", 1)
    por_pagina = filtros.pop("por_pagina", 100)
    pedidos = services.filtrar_pedidos(**filtros)
    paginador = Paginator(export.preparar_pedidos(pedidos), por_pagina)
    try:
        pagina = paginador.page(numero)
    except EmptyPage:
        return _error("pagina_no_encontrada", "La página solicitada no existe.", 404)

    def enlace_pagina(num):
        consulta = request.GET.copy()
        consulta["pagina"] = num
        return f"{request.path}?{consulta.urlencode()}"

    return JsonResponse({
        "version": 1,
        "generado_en": timezone.localtime().isoformat(),
        "zona_horaria": timezone.get_current_timezone_name(),
        "moneda": "COP",
        "filtros": filtros,
        **export.agregados(pedidos),
        "pedidos": [export.serializar_pedido(pedido) for pedido in pagina],
        "paginacion": {
            "pagina": pagina.number,
            "por_pagina": por_pagina,
            "total_pedidos": paginador.count,
            "total_paginas": paginador.num_pages,
            "siguiente": enlace_pagina(pagina.next_page_number()) if pagina.has_next() else None,
            "anterior": enlace_pagina(pagina.previous_page_number()) if pagina.has_previous() else None,
        },
        "inventario": export.inventario_actual(),
    })

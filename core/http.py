from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def es_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def destino_seguro(request, por_defecto, campo="siguiente"):
    """URL de retorno enviada por el formulario, solo si apunta a este sitio."""
    destino = request.POST.get(campo) or request.GET.get(campo)
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return por_defecto


def responder_accion(request, mensaje, destino, *, ok=True, nivel=None, datos=None):
    """Responde una acción POST: JSON si viene de fetch(), redirección + mensaje si no."""
    nivel = nivel or ("success" if ok else "danger")
    if es_ajax(request):
        cuerpo = {"ok": ok, "mensaje": mensaje, "nivel": nivel, **(datos or {})}
        return JsonResponse(cuerpo, status=200 if ok else 400)
    nivel_mensaje = {
        "success": messages.SUCCESS,
        "info": messages.INFO,
        "warning": messages.WARNING,
        "danger": messages.ERROR,
    }[nivel]
    messages.add_message(request, nivel_mensaje, mensaje)
    return redirect(destino)

from .navegacion import elementos_menu


def navegacion(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {"menu_navegacion": []}
    return {"menu_navegacion": elementos_menu(usuario, request.path)}

from .cart import Carrito


def carrito(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated or not usuario.es_cliente:
        return {}
    return {"carrito_cantidad": len(Carrito(request))}

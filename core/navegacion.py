"""Navegación y página de inicio dependientes del rol del usuario."""
from django.urls import NoReverseMatch, reverse

from accounts.models import Rol

URL_INICIO_POR_ROL = {
    Rol.Nombre.CLIENTE: "menu:catalogo",
    Rol.Nombre.OPERARIO: "orders:operario_pedidos",
    Rol.Nombre.ADMINISTRADOR: "reports:dashboard",
}
URL_INICIO_POR_DEFECTO = "accounts:perfil"

MENU_POR_ROL = {
    Rol.Nombre.CLIENTE: (
        ("Inicio", "accounts:inicio", "bi-house"),
        ("Menú", "menu:catalogo", "bi-journal-text"),
        ("Carrito", "orders:carrito", "bi-cart3"),
        ("Mis pedidos", "orders:mis_pedidos", "bi-bag-check"),
        ("Mi perfil", "accounts:perfil", "bi-person-circle"),
    ),
    Rol.Nombre.OPERARIO: (
        ("Pedidos activos", "orders:operario_pedidos", "bi-fire"),
        ("Menú", "menu:catalogo", "bi-journal-text"),
    ),
    Rol.Nombre.ADMINISTRADOR: (
        ("Dashboard", "reports:dashboard", "bi-speedometer2"),
        ("Pedidos", "reports:tabular", "bi-receipt"),
        ("Menú", "menu:admin_lista", "bi-journal-text"),
        ("Informes", "reports:informes", "bi-bar-chart-line"),
    ),
}


def _resolver(nombre_url):
    try:
        return reverse(nombre_url)
    except NoReverseMatch:
        return None


def url_inicio(usuario):
    """URL a la que se redirige a cada rol tras iniciar sesión."""
    nombre_url = URL_INICIO_POR_ROL.get(getattr(usuario.rol, "nombre", None))
    return (nombre_url and _resolver(nombre_url)) or reverse(URL_INICIO_POR_DEFECTO)


def elementos_menu(usuario, ruta_actual=""):
    """Enlaces del navbar para el rol del usuario (omite rutas aún no registradas)."""
    elementos = []
    for etiqueta, nombre_url, icono in MENU_POR_ROL.get(usuario.rol.nombre, ()):
        url = _resolver(nombre_url)
        if url is None:
            continue
        elementos.append({
            "etiqueta": etiqueta,
            "url": url,
            "icono": icono,
            "activo": ruta_actual == url,
        })
    return elementos

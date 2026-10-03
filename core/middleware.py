from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import Resolver404, resolve


class LoginRequeridoMiddleware:
    """Exige sesión iniciada en toda la aplicación salvo las rutas públicas.

    Es una capa adicional: cada vista protegida declara además su rol
    permitido mediante decoradores o mixins.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.nombres_publicos = set(settings.LOGIN_EXEMPT_URL_NAMES)
        self.prefijos_publicos = tuple(settings.LOGIN_EXEMPT_PATH_PREFIXES)

    def __call__(self, request):
        if not request.user.is_authenticated and not self._es_publica(request.path_info):
            return redirect_to_login(request.get_full_path())
        return self.get_response(request)

    def _es_publica(self, ruta):
        if ruta.startswith(self.prefijos_publicos):
            return True
        try:
            coincidencia = resolve(ruta)
        except Resolver404:
            return False
        return coincidencia.view_name in self.nombres_publicos

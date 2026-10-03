"""Control de acceso basado en roles (decoradores para FBV y mixins para CBV).

La autorización se valida siempre en el servidor: un usuario que escriba
manualmente una URL de otro rol recibe HTTP 403.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied

from .models import Rol


def rol_requerido(*roles):
    if not roles:
        raise ImproperlyConfigured("rol_requerido necesita al menos un rol.")

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if not request.user.tiene_rol(*roles):
                raise PermissionDenied("No tiene permisos para acceder a esta sección.")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


cliente_requerido = rol_requerido(Rol.Nombre.CLIENTE)
operario_requerido = rol_requerido(Rol.Nombre.OPERARIO)
administrador_requerido = rol_requerido(Rol.Nombre.ADMINISTRADOR)


class RolRequeridoMixin(LoginRequiredMixin):
    roles_permitidos = ()

    def dispatch(self, request, *args, **kwargs):
        if not self.roles_permitidos:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} debe definir roles_permitidos."
            )
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.tiene_rol(*self.roles_permitidos):
            raise PermissionDenied("No tiene permisos para acceder a esta sección.")
        return super().dispatch(request, *args, **kwargs)


class ClienteRequeridoMixin(RolRequeridoMixin):
    roles_permitidos = (Rol.Nombre.CLIENTE,)


class OperarioRequeridoMixin(RolRequeridoMixin):
    roles_permitidos = (Rol.Nombre.OPERARIO,)


class AdministradorRequeridoMixin(RolRequeridoMixin):
    roles_permitidos = (Rol.Nombre.ADMINISTRADOR,)

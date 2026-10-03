from django.apps import apps
from django.contrib.auth.base_user import BaseUserManager


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _obtener_rol(self, nombre_rol):
        Rol = apps.get_model("accounts", "Rol")
        rol, _ = Rol.objects.get_or_create(nombre=nombre_rol)
        return rol

    def _crear_usuario(self, email, password, **campos):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico.")
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **campos):
        from .models import Rol

        campos.setdefault("is_superuser", False)
        if "rol" not in campos and "rol_id" not in campos:
            campos["rol"] = self._obtener_rol(Rol.Nombre.CLIENTE)
        return self._crear_usuario(email, password, **campos)

    def create_superuser(self, email, password=None, **campos):
        from .models import Rol

        campos["is_superuser"] = True
        campos.setdefault("rol", self._obtener_rol(Rol.Nombre.ADMINISTRADOR))
        return self._crear_usuario(email, password, **campos)

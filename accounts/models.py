from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UsuarioManager


class Rol(models.Model):
    """Tabla `roles` del modelo de datos (Roles 1 ─── N Usuarios)."""

    class Nombre(models.TextChoices):
        CLIENTE = "Cliente", "Cliente"
        OPERARIO = "Operario", "Operario"
        ADMINISTRADOR = "Administrador", "Administrador"

    id = models.BigAutoField(primary_key=True, db_column="id_rol")
    nombre = models.CharField(max_length=30, choices=Nombre.choices, unique=True)

    class Meta:
        db_table = "roles"
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["id"]

    def __str__(self):
        return self.nombre


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Tabla `usuarios`. La contraseña se guarda con el hashing de Django."""

    id = models.BigAutoField(primary_key=True, db_column="id_usuario")
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        related_name="usuarios",
        db_column="id_rol",
    )
    nombre = models.CharField(max_length=150)
    email = models.EmailField("correo electrónico", max_length=254, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField("activo", default=True, db_column="activo")
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    direccion = models.CharField("dirección", max_length=255, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["rol", "is_active"], name="usuarios_rol_activo_idx"),
        ]

    def __str__(self):
        return f"{self.nombre} <{self.email}>"

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        super().save(*args, **kwargs)

    @property
    def activo(self):
        return self.is_active

    @property
    def is_staff(self):
        """Solo administradores y superusuarios acceden al admin de Django."""
        return self.is_superuser or self.es_administrador

    def tiene_rol(self, *nombres_rol):
        return self.rol_id is not None and self.rol.nombre in nombres_rol

    @property
    def es_cliente(self):
        return self.tiene_rol(Rol.Nombre.CLIENTE)

    @property
    def es_operario(self):
        return self.tiene_rol(Rol.Nombre.OPERARIO)

    @property
    def es_administrador(self):
        return self.tiene_rol(Rol.Nombre.ADMINISTRADOR)

    def get_full_name(self):
        return self.nombre

    def get_short_name(self):
        return self.nombre.split(" ")[0] if self.nombre else self.email

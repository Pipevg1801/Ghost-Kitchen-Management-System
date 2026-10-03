"""Utilidades compartidas por los tests de las distintas apps."""
from decimal import Decimal

from accounts.models import Rol, Usuario
from menu.models import Plato

PASSWORD = "ClaveSegura#2026"


def crear_usuario(email, rol_nombre, **extra):
    return Usuario.objects.create_user(
        email=email, password=PASSWORD, nombre=extra.pop("nombre", email.split("@")[0]),
        rol=Rol.objects.get(nombre=rol_nombre), **extra,
    )


def crear_plato(nombre="Ítem del menú #1", precio="12345.00", disponible=10, **extra):
    return Plato.objects.create(
        nombre=nombre, precio=Decimal(precio), cantidad_disponible=disponible, **extra
    )


class UsuariosPorRolMixin:
    """Crea un usuario por rol en setUpTestData."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cliente = crear_usuario("cliente@test.com", Rol.Nombre.CLIENTE, nombre="Pepito Perez")
        cls.cliente2 = crear_usuario("cliente2@test.com", Rol.Nombre.CLIENTE, nombre="Felipe Vargas")
        cls.operario = crear_usuario("operario@test.com", Rol.Nombre.OPERARIO)
        cls.admin = crear_usuario("admin@test.com", Rol.Nombre.ADMINISTRADOR)

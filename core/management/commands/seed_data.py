"""Carga datos iniciales de desarrollo: roles, usuarios de prueba y platos.

Es idempotente: puede ejecutarse varias veces sin duplicar registros.
Las contraseñas son exclusivamente para el entorno local.

Con --pedidos N crea además N pedidos de demostración repartidos en los
últimos 14 días (usando los mismos servicios que la aplicación), para
poder evaluar el panel del operario y los informes.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Rol, Usuario
from menu.models import Plato
from orders import services
from orders.models import Pedido

USUARIOS_PRUEBA = (
    {"email": "admin@example.com", "nombre": "Administrador Demo",
     "rol": Rol.Nombre.ADMINISTRADOR, "password": "AdminDemo#2026"},
    {"email": "operario@example.com", "nombre": "Operario Demo",
     "rol": Rol.Nombre.OPERARIO, "password": "OperarioDemo#2026"},
    {"email": "cliente@example.com", "nombre": "Pepito Perez",
     "rol": Rol.Nombre.CLIENTE, "password": "ClienteDemo#2026",
     "telefono": "3001234567", "direccion": "Calle 45 # 27-10, Bucaramanga"},
    {"email": "cliente2@example.com", "nombre": "Felipe Vargas",
     "rol": Rol.Nombre.CLIENTE, "password": "ClienteDemo#2026",
     "telefono": "3109876543", "direccion": "Carrera 33 # 52-18, Bucaramanga"},
)

PLATOS_PRUEBA = (
    ("Ítem del menú #1", "12345.00", "Hamburguesa artesanal con queso madurado y papas rústicas.", 40),
    ("Ítem del menú #2", "98765.00", "Parrillada para compartir: res, cerdo, pollo y chorizo.", 15),
    ("Ítem del menú #3", "24691.00", "Bowl de pollo teriyaki con arroz jazmín y vegetales salteados.", 30),
    ("Ítem del menú #4", "18500.00", "Pasta al pesto con tomates cherry y parmesano.", 25),
    ("Ítem del menú #5", "9900.00", "Limonada de coco natural (500 ml).", 60),
)


class Command(BaseCommand):
    help = "Crea roles, usuarios de prueba (uno por rol) y platos del menú."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pedidos", type=int, default=0,
            help="Número de pedidos de demostración a generar (por defecto 0).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        roles = {nombre: Rol.objects.get_or_create(nombre=nombre)[0] for nombre in Rol.Nombre.values}
        self.stdout.write(f"Roles: {', '.join(roles)}")

        for datos in USUARIOS_PRUEBA:
            datos = dict(datos)
            password = datos.pop("password")
            rol = roles[datos.pop("rol")]
            usuario, creado = Usuario.objects.update_or_create(
                email=datos.pop("email"),
                defaults={**datos, "rol": rol, "is_active": True,
                          "is_superuser": rol.nombre == Rol.Nombre.ADMINISTRADOR},
            )
            usuario.set_password(password)
            usuario.save(update_fields=["password"])
            self.stdout.write(f"  {'Creado' if creado else 'Actualizado'}: {usuario.email} ({rol})")

        for nombre, precio, descripcion, disponible in PLATOS_PRUEBA:
            _, creado = Plato.objects.get_or_create(
                nombre=nombre,
                defaults={"precio": Decimal(precio), "descripcion": descripcion,
                          "cantidad_disponible": disponible, "cantidad_reservada": 0},
            )
            self.stdout.write(f"  {'Creado' if creado else 'Existente'}: {nombre}")

        if options["pedidos"] > 0:
            self._crear_pedidos_demo(options["pedidos"])

        self.stdout.write(self.style.SUCCESS("Datos de prueba cargados."))

    def _crear_pedidos_demo(self, cantidad):
        azar = random.Random(2026)
        clientes = list(Usuario.objects.filter(rol__nombre=Rol.Nombre.CLIENTE))
        Estado = Pedido.Estado
        creados = 0
        for _ in range(cantidad):
            disponibles = list(Plato.objects.con_disponibilidad())
            if not disponibles:
                self.stdout.write(self.style.WARNING("  Sin disponibilidad para más pedidos."))
                break
            elegidos = azar.sample(disponibles, k=min(len(disponibles), azar.randint(1, 3)))
            cantidades = {p.pk: min(p.cantidad_disponible, azar.randint(1, 2)) for p in elegidos}
            pedido = services.confirmar_pedido(azar.choice(clientes), cantidades)

            dias_atras = azar.randint(0, 13)
            destino = azar.choices(
                [Estado.RECIBIDO, Estado.EN_PREPARACION, Estado.LISTO, Estado.CANCELADO],
                weights=[2, 2, 5, 1] if dias_atras == 0 else [0, 0, 9, 1],
            )[0]
            if destino == Estado.CANCELADO:
                services.cancelar_pedido(pedido.pk, pedido.usuario)
            else:
                flujo = [Estado.EN_PREPARACION, Estado.LISTO]
                for estado in flujo[:flujo.index(destino) + 1] if destino in flujo else []:
                    services.cambiar_estado(pedido.pk, estado)

            fecha = timezone.now() - timedelta(days=dias_atras, minutes=azar.randint(0, 600))
            Pedido.objects.filter(pk=pedido.pk).update(fecha_creacion=fecha)
            creados += 1
        self.stdout.write(f"  Pedidos de demostración creados: {creados}")

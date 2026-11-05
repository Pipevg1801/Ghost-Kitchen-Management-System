from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import Usuario
from core.tests_utils import crear_usuario, crear_plato
from menu.models import Plato
from . import services
from .models import Pedido
from io import StringIO

class ConfirmarPedidoServicioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = crear_usuario("cliente.cp01@example.com", "Cliente")
        cls.plato = crear_plato(
            nombre="Plato de prueba", precio="10000.00", disponible=10
        )
    
    def test_confirmar_pedido_con_stock_suficiente(self):
        pedido = services.confirmar_pedido(self.cliente, {self.plato.pk: 3})

        # El pedido queda en estado Recibido con el total calculado
        self.assertEqual(pedido.estado, Pedido.Estado.RECIBIDO)
        self.assertEqual(pedido.total, Decimal("30000.00"))

        # El detalle guarda la cantidad y el precio histórico
        detalle = pedido.detalles.get()
        self.assertEqual(detalle.cantidad, 3)
        self.assertEqual(detalle.precio_unitario, Decimal("10000.00"))

        # El inventario se actualizó: 10/0 -> 7/3
        self.plato.refresh_from_db()
        self.assertEqual(self.plato.cantidad_disponible, 7)
        self.assertEqual(self.plato.cantidad_reservada, 3)

    def test_confirmar_pedido_sin_stock_suficiente(self):
        # Se parte del estado que deja el escenario A: plato en 7/3
        services.confirmar_pedido(self.cliente, {self.plato.pk: 3})

        # Se piden 8 unidades pero solo hay 7 disponibles
        with self.assertRaises(services.DisponibilidadInsuficiente) as contexto:
            services.confirmar_pedido(self.cliente, {self.plato.pk: 8})

        self.assertEqual(
            str(contexto.exception),
            "No hay suficiente disponibilidad: Plato de prueba (disponibles: 7).",
        )

        # No se creó un segundo pedido
        self.assertEqual(Pedido.objects.filter(usuario=self.cliente).count(), 1)

        # El inventario no cambió: sigue 7/3
        self.plato.refresh_from_db()
        self.assertEqual(self.plato.cantidad_disponible, 7)
        self.assertEqual(self.plato.cantidad_reservada, 3)
    
class CancelarPedidoServicioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = crear_usuario("cliente.cp02@example.com", "Cliente")
        cls.plato = crear_plato(
            nombre="Plato de prueba", precio="10000.00", disponible=10
        )

    def test_cancelar_pedido_recibido_devuelve_inventario(self):
        # P1: 3 unidades -> plato en 7/3
        p1 = services.confirmar_pedido(self.cliente, {self.plato.pk: 3})

        cancelado = services.cancelar_pedido(p1.pk, self.cliente)

        self.assertEqual(cancelado.estado, Pedido.Estado.CANCELADO)
        self.plato.refresh_from_db()
        self.assertEqual(self.plato.cantidad_disponible, 10)
        self.assertEqual(self.plato.cantidad_reservada, 0)

    def test_no_cancela_pedido_en_preparacion(self):
        # P2: 2 unidades -> plato en 8/2, luego pasa a En preparación
        p2 = services.confirmar_pedido(self.cliente, {self.plato.pk: 2})
        services.cambiar_estado(p2.pk, Pedido.Estado.EN_PREPARACION)

        with self.assertRaises(services.PedidoNoCancelable) as contexto:
            services.cancelar_pedido(p2.pk, self.cliente)

        self.assertEqual(
            str(contexto.exception),
            "Solo se pueden cancelar pedidos en estado «Recibido»; "
            "este pedido ya está en cocina.",
        )

        # El pedido sigue en preparación y el inventario no cambió: 8/2
        p2.refresh_from_db()
        self.assertEqual(p2.estado, Pedido.Estado.EN_PREPARACION)
        self.plato.refresh_from_db()
        self.assertEqual(self.plato.cantidad_disponible, 8)
        self.assertEqual(self.plato.cantidad_reservada, 2)



class FlujoCompletoPedidoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Carga los usuarios y los platos de demostración (seed_data)
        call_command("seed_data", stdout=StringIO())
        cls.cliente = Usuario.objects.get(email="cliente@example.com")
        cls.operario = Usuario.objects.get(email="operario@example.com")
        cls.admin = Usuario.objects.get(email="admin@example.com")
        cls.plato1 = Plato.objects.get(nombre="Ítem del menú #1")
        cls.plato5 = Plato.objects.get(nombre="Ítem del menú #5")

    def test_flujo_completo_de_un_pedido(self):
        # --- 1. El cliente inicia sesión ---
        respuesta = self.client.post(
            reverse("accounts:login"),
            {"username": "cliente@example.com", "password": "ClienteDemo#2026"},
            follow=True,
        )
        self.assertContains(respuesta, "Bienvenido, Pepito.")

        # --- 2. Agrega 2 x Ítem #1 y 1 x Ítem #5 al carrito ---
        self.client.post(reverse("orders:carrito_agregar"),
                         {"plato_id": self.plato1.pk, "cantidad": 2})
        self.client.post(reverse("orders:carrito_agregar"),
                         {"plato_id": self.plato5.pk, "cantidad": 1})

        # --- 3. Confirma el pedido ---
        respuesta = self.client.post(reverse("orders:pedido_confirmar"), follow=True)
        pedido = Pedido.objects.get()
        self.assertContains(respuesta, f"Pedido #{pedido.pk} creado correctamente.")
        self.assertEqual(pedido.estado, Pedido.Estado.RECIBIDO)
        self.assertEqual(pedido.total, Decimal("34590.00"))

        # El inventario bajó: #1 en 38 y #5 en 59
        self.plato1.refresh_from_db()
        self.plato5.refresh_from_db()
        self.assertEqual(self.plato1.cantidad_disponible, 38)
        self.assertEqual(self.plato5.cantidad_disponible, 59)

        # --- 4. El cliente intenta entrar al panel del operario: 403 ---
        respuesta = self.client.get(reverse("orders:operario_pedidos"))
        self.assertEqual(respuesta.status_code, 403)

        # --- 5. El operario inicia sesión y ve el pedido en su panel ---
        self.client.logout()
        self.client.post(
            reverse("accounts:login"),
            {"username": "operario@example.com", "password": "OperarioDemo#2026"},
        )
        respuesta = self.client.get(reverse("orders:operario_pedidos"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f"Pedido #{pedido.pk}")

        # --- 6. Marca "En preparación" y luego "Listo" ---
        url_estado = reverse("orders:operario_cambiar_estado", args=[pedido.pk])
        self.client.post(url_estado, {"estado": Pedido.Estado.EN_PREPARACION})
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.EN_PREPARACION)

        self.client.post(url_estado, {"estado": Pedido.Estado.LISTO})
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.LISTO)

        # El pedido aparece en "Listos hoy" del panel
        respuesta = self.client.get(reverse("orders:operario_pedidos"))
        self.assertIn(pedido, respuesta.context["pedidos_listos"])

        # Al quedar listo, las reservas se liberan (se consumieron)
        self.plato1.refresh_from_db()
        self.assertEqual(self.plato1.cantidad_reservada, 0)
        
        # --- 7. El cliente ve su pedido como Listo en "Mis pedidos" ---
        self.client.logout()
        self.client.post(
            reverse("accounts:login"),
            {"username": "cliente@example.com", "password": "ClienteDemo#2026"},
        )
        respuesta = self.client.get(reverse("orders:mis_pedidos"))
        self.assertContains(respuesta, f"Pedido #{pedido.pk}")
        self.assertContains(respuesta, "Listo")

        # --- 8. El administrador revisa los informes ---
        self.client.logout()
        self.client.post(
            reverse("accounts:login"),
            {"username": "admin@example.com", "password": "AdminDemo#2026"},
        )

        # Informe consolidado: +1 pedido, +$34.590, cancelados sin cambio
        respuesta = self.client.get(reverse("reports:consolidado"))
        self.assertEqual(respuesta.status_code, 200)
        resumen = respuesta.context["resumen"]
        self.assertEqual(resumen["pedidos"], 1)
        self.assertEqual(resumen["ingresos"], Decimal("34590.00"))
        self.assertEqual(resumen["cancelados"], 0)

        # Informe tabular: el pedido aparece y la suma se muestra formateada
        respuesta = self.client.get(reverse("reports:tabular"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(pedido, respuesta.context["pedidos"])
        self.assertContains(respuesta, "$34.590")
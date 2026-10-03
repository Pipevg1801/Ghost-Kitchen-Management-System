from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.tests_utils import UsuariosPorRolMixin, crear_plato
from menu.models import Plato

from . import services
from .cart import CLAVE_SESION
from .models import Pedido

Estado = Pedido.Estado
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class CarritoTests(UsuariosPorRolMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plato1 = crear_plato("Ítem del menú #1", "12345.00", disponible=5)
        cls.plato2 = crear_plato("Ítem del menú #2", "98765.00", disponible=2)

    def setUp(self):
        self.client.force_login(self.cliente)

    def carrito(self):
        return {int(k): v for k, v in self.client.session.get(CLAVE_SESION, {}).items()}

    def agregar(self, plato, cantidad=1, **extra):
        return self.client.post(reverse("orders:carrito_agregar"),
                                {"plato_id": plato.pk, "cantidad": cantidad}, **extra)

    def modificar(self, plato, accion, **extra):
        return self.client.post(reverse("orders:carrito_modificar"),
                                {"plato_id": plato.pk, "accion": accion}, **extra)

    def test_agregar_producto(self):
        respuesta = self.agregar(self.plato1, follow=True)
        self.assertContains(respuesta, "producto agregado al carrito.")
        self.assertEqual(self.carrito(), {self.plato1.pk: 1})

    def test_agregar_producto_existente_suma_cantidad(self):
        self.agregar(self.plato1, 2)
        self.agregar(self.plato1, 1)
        self.assertEqual(self.carrito(), {self.plato1.pk: 3})

    def test_no_supera_la_disponibilidad(self):
        self.agregar(self.plato2, 2)
        respuesta = self.agregar(self.plato2, 1, follow=True)
        self.assertContains(respuesta, "No hay suficiente disponibilidad")
        self.assertEqual(self.carrito(), {self.plato2.pk: 2})

    def test_no_agrega_plato_inactivo(self):
        oculto = crear_plato("Oculto", activo=False)
        self.agregar(oculto)
        self.assertEqual(self.carrito(), {})

    def test_cantidad_invalida(self):
        self.agregar(self.plato1, 0)
        self.assertEqual(self.carrito(), {})

    def test_incrementar_cantidad(self):
        self.agregar(self.plato1)
        self.modificar(self.plato1, "incrementar")
        self.assertEqual(self.carrito(), {self.plato1.pk: 2})

    def test_incrementar_respeta_disponibilidad(self):
        self.agregar(self.plato2, 2)
        respuesta = self.modificar(self.plato2, "incrementar", **AJAX)
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()["ok"])
        self.assertEqual(self.carrito(), {self.plato2.pk: 2})

    def test_disminuir_cantidad(self):
        self.agregar(self.plato1, 3)
        self.modificar(self.plato1, "disminuir")
        self.assertEqual(self.carrito(), {self.plato1.pk: 2})

    def test_disminuir_hasta_cero_elimina(self):
        self.agregar(self.plato1)
        self.modificar(self.plato1, "disminuir")
        self.assertEqual(self.carrito(), {})

    def test_eliminar_producto(self):
        self.agregar(self.plato1)
        self.agregar(self.plato2)
        respuesta = self.client.post(reverse("orders:carrito_eliminar"), {"plato_id": self.plato1.pk}, follow=True)
        self.assertContains(respuesta, "Producto eliminado del carrito.")
        self.assertEqual(self.carrito(), {self.plato2.pk: 1})

    def test_cancelar_carrito(self):
        self.agregar(self.plato1)
        self.agregar(self.plato2)
        self.client.post(reverse("orders:carrito_cancelar"))
        self.assertEqual(self.carrito(), {})

    def test_vista_carrito_calcula_subtotal_y_total(self):
        self.agregar(self.plato1, 2)
        self.agregar(self.plato2, 1)
        respuesta = self.client.get(reverse("orders:carrito"))
        resumen = respuesta.context["carrito"]
        self.assertEqual(resumen["total"], Decimal("123455.00"))
        self.assertEqual(resumen["cantidad"], 3)
        self.assertContains(respuesta, "$24.690")
        self.assertContains(respuesta, "$123.455")

    def test_respuesta_ajax_incluye_carrito_actualizado(self):
        respuesta = self.agregar(self.plato1, 2, **AJAX)
        datos = respuesta.json()
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["carrito"]["cantidad"], 2)
        self.assertEqual(datos["carrito"]["por_plato"], {str(self.plato1.pk): 2})
        self.assertIn("$24.690", datos["carrito"]["html_completo"])

    def test_precio_del_navegador_se_ignora(self):
        self.client.post(reverse("orders:carrito_agregar"),
                         {"plato_id": self.plato1.pk, "cantidad": 1, "precio": "1"})
        self.client.post(reverse("orders:pedido_confirmar"), {"total": "1"})
        self.assertEqual(Pedido.objects.get().total, Decimal("12345.00"))

    def test_solo_clientes_usan_el_carrito(self):
        for usuario in (self.operario, self.admin):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("orders:carrito")).status_code, 403)
            self.assertEqual(self.agregar(self.plato1).status_code, 403)


class ConfirmarPedidoTests(UsuariosPorRolMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plato1 = crear_plato("Ítem del menú #1", "12345.00", disponible=5)
        cls.plato2 = crear_plato("Ítem del menú #2", "98765.00", disponible=2)

    def setUp(self):
        self.client.force_login(self.cliente)

    def llenar_carrito(self, cantidades):
        for plato, cantidad in cantidades:
            self.client.post(reverse("orders:carrito_agregar"), {"plato_id": plato.pk, "cantidad": cantidad})

    def test_crear_pedido_desde_carrito(self):
        self.llenar_carrito([(self.plato1, 2), (self.plato2, 1)])
        respuesta = self.client.post(reverse("orders:pedido_confirmar"), follow=True)
        pedido = Pedido.objects.get()
        self.assertRedirects(respuesta, reverse("orders:pedido_detalle", args=[pedido.pk]))
        self.assertContains(respuesta, f"Pedido #{pedido.pk} creado correctamente.")
        self.assertEqual(pedido.usuario, self.cliente)
        self.assertEqual(pedido.estado, Estado.RECIBIDO)
        self.assertEqual(pedido.detalles.count(), 2)
        self.assertIsNotNone(pedido.fecha_creacion)
        self.assertEqual(self.client.session[CLAVE_SESION], {})

    def test_calcular_total_en_backend(self):
        self.llenar_carrito([(self.plato1, 2), (self.plato2, 1)])
        self.client.post(reverse("orders:pedido_confirmar"))
        self.assertEqual(Pedido.objects.get().total, Decimal("123455.00"))

    def test_actualiza_inventario(self):
        self.llenar_carrito([(self.plato1, 2)])
        self.client.post(reverse("orders:pedido_confirmar"))
        self.plato1.refresh_from_db()
        self.assertEqual((self.plato1.cantidad_disponible, self.plato1.cantidad_reservada), (3, 2))

    def test_guarda_precio_historico(self):
        self.llenar_carrito([(self.plato1, 1)])
        self.client.post(reverse("orders:pedido_confirmar"))
        Plato.objects.filter(pk=self.plato1.pk).update(precio=Decimal("50000"))
        detalle = Pedido.objects.get().detalles.get()
        self.assertEqual(detalle.precio_unitario, Decimal("12345.00"))

    def test_carrito_vacio_no_crea_pedido(self):
        respuesta = self.client.post(reverse("orders:pedido_confirmar"), follow=True)
        self.assertContains(respuesta, "El carrito está vacío")
        self.assertFalse(Pedido.objects.exists())

    def test_valida_disponibilidad_al_confirmar(self):
        self.llenar_carrito([(self.plato1, 1), (self.plato2, 2)])
        Plato.objects.filter(pk=self.plato2.pk).update(cantidad_disponible=1)
        respuesta = self.client.post(reverse("orders:pedido_confirmar"), follow=True)
        self.assertContains(respuesta, "No hay suficiente disponibilidad")
        self.assertFalse(Pedido.objects.exists())
        self.plato1.refresh_from_db()
        self.assertEqual(self.plato1.cantidad_disponible, 5)

    def test_servicio_rechaza_cantidades_no_positivas(self):
        with self.assertRaises(services.ErrorPedido):
            services.confirmar_pedido(self.cliente, {self.plato1.pk: 0})


class PedidosClienteTests(UsuariosPorRolMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plato = crear_plato(disponible=10)

    def setUp(self):
        self.pedido = services.confirmar_pedido(self.cliente, {self.plato.pk: 3})

    def test_mis_pedidos_muestra_solo_los_propios(self):
        ajeno = services.confirmar_pedido(self.cliente2, {self.plato.pk: 1})
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("orders:mis_pedidos"))
        self.assertEqual(list(respuesta.context["pedidos"]), [self.pedido])
        self.assertNotContains(respuesta, f"Pedido #{ajeno.pk}")

    def test_detalle_ajeno_da_404(self):
        self.client.force_login(self.cliente2)
        self.assertEqual(
            self.client.get(reverse("orders:pedido_detalle", args=[self.pedido.pk])).status_code, 404
        )

    def test_operario_y_admin_ven_detalle(self):
        for usuario in (self.operario, self.admin):
            self.client.force_login(usuario)
            respuesta = self.client.get(reverse("orders:pedido_detalle", args=[self.pedido.pk]))
            self.assertEqual(respuesta.status_code, 200)

    def test_cancelar_pedido_recibido(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(reverse("orders:pedido_cancelar", args=[self.pedido.pk]), follow=True)
        self.assertContains(respuesta, "cancelado")
        self.pedido.refresh_from_db()
        self.plato.refresh_from_db()
        self.assertEqual(self.pedido.estado, Estado.CANCELADO)
        self.assertEqual((self.plato.cantidad_disponible, self.plato.cantidad_reservada), (10, 0))

    def test_no_cancela_pedido_en_preparacion(self):
        services.cambiar_estado(self.pedido.pk, Estado.EN_PREPARACION)
        self.client.force_login(self.cliente)
        respuesta = self.client.post(reverse("orders:pedido_cancelar", args=[self.pedido.pk]), **AJAX)
        self.assertEqual(respuesta.status_code, 400)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Estado.EN_PREPARACION)

    def test_no_cancela_pedido_ajeno(self):
        self.client.force_login(self.cliente2)
        respuesta = self.client.post(reverse("orders:pedido_cancelar", args=[self.pedido.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Estado.RECIBIDO)

    def test_operario_no_cancela_pedidos(self):
        self.client.force_login(self.operario)
        respuesta = self.client.post(reverse("orders:pedido_cancelar", args=[self.pedido.pk]))
        self.assertEqual(respuesta.status_code, 403)


class PanelOperarioTests(UsuariosPorRolMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plato = crear_plato(disponible=10)

    def setUp(self):
        self.pedido = services.confirmar_pedido(self.cliente, {self.plato.pk: 2})
        self.client.force_login(self.operario)

    def cambiar(self, estado, **extra):
        return self.client.post(
            reverse("orders:operario_cambiar_estado", args=[self.pedido.pk]), {"estado": estado}, **extra
        )

    def test_pedidos_activos_muestra_pedido(self):
        respuesta = self.client.get(reverse("orders:operario_pedidos"))
        self.assertContains(respuesta, "Pedidos activos")
        self.assertContains(respuesta, f"Pedido #{self.pedido.pk} - Pepito Perez")
        self.assertContains(respuesta, "Marcar en preparación")

    def test_flujo_completo_de_estados(self):
        respuesta = self.cambiar(Estado.EN_PREPARACION, follow=True)
        self.assertContains(respuesta, "Estado del pedido actualizado")
        self.assertContains(respuesta, "Marcar listo")
        self.cambiar(Estado.LISTO)
        self.pedido.refresh_from_db()
        self.plato.refresh_from_db()
        self.assertEqual(self.pedido.estado, Estado.LISTO)
        self.assertEqual((self.plato.cantidad_disponible, self.plato.cantidad_reservada), (8, 0))

    def test_listo_queda_identificado(self):
        self.cambiar(Estado.EN_PREPARACION)
        self.cambiar(Estado.LISTO)
        respuesta = self.client.get(reverse("orders:operario_pedidos"))
        self.assertIn(self.pedido, respuesta.context["pedidos_listos"])
        self.assertNotIn(self.pedido, respuesta.context["pedidos_activos"])
        self.assertContains(respuesta, "tarjeta-pedido-listo")

    def test_no_permite_saltar_estados(self):
        respuesta = self.cambiar(Estado.LISTO, **AJAX)
        self.assertEqual(respuesta.status_code, 400)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Estado.RECIBIDO)

    def test_no_permite_retroceder(self):
        self.cambiar(Estado.EN_PREPARACION)
        self.cambiar(Estado.LISTO)
        for estado in (Estado.RECIBIDO, Estado.EN_PREPARACION, Estado.CANCELADO):
            self.cambiar(estado)
            self.pedido.refresh_from_db()
            self.assertEqual(self.pedido.estado, Estado.LISTO)

    def test_estado_inexistente(self):
        respuesta = self.cambiar("INVENTADO", **AJAX)
        self.assertEqual(respuesta.status_code, 400)

    def test_parcial_ajax_para_autorefresco(self):
        respuesta = self.client.get(reverse("orders:operario_pedidos"), **AJAX)
        self.assertTemplateUsed(respuesta, "orders/operario/_tablero.html")
        self.assertTemplateNotUsed(respuesta, "base.html")

    def test_cliente_y_admin_no_acceden_al_panel(self):
        for usuario in (self.cliente, self.admin):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("orders:operario_pedidos")).status_code, 403)
            self.assertEqual(self.cambiar(Estado.EN_PREPARACION).status_code, 403)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Estado.RECIBIDO)

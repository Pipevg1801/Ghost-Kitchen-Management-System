from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Usuario
from menu.models import Plato

from .models import Pedido, PedidoDetalle

Estado = Pedido.Estado


class PedidoModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = Usuario.objects.create_user(
            email="cliente@test.com", password="ClaveSegura#2026", nombre="Pepito Perez"
        )
        cls.plato1 = Plato.objects.create(nombre="Ítem #1", precio=Decimal("12345.00"),
                                          cantidad_disponible=10)
        cls.plato2 = Plato.objects.create(nombre="Ítem #2", precio=Decimal("98765.00"),
                                          cantidad_disponible=10)

    def crear_pedido(self, **campos):
        return Pedido.objects.create(usuario=self.cliente, **campos)

    def test_estado_inicial_recibido(self):
        self.assertEqual(self.crear_pedido().estado, Estado.RECIBIDO)

    def test_transiciones_permitidas(self):
        pedido = self.crear_pedido()
        self.assertTrue(pedido.puede_transicionar_a(Estado.EN_PREPARACION))
        self.assertFalse(pedido.puede_transicionar_a(Estado.LISTO))
        pedido.estado = Estado.EN_PREPARACION
        self.assertTrue(pedido.puede_transicionar_a(Estado.LISTO))
        self.assertFalse(pedido.puede_transicionar_a(Estado.RECIBIDO))

    def test_listo_y_cancelado_no_tienen_siguiente_estado(self):
        for estado in (Estado.LISTO, Estado.CANCELADO):
            pedido = Pedido(usuario=self.cliente, estado=estado)
            self.assertIsNone(pedido.siguiente_estado)
            self.assertFalse(pedido.puede_transicionar_a(Estado.RECIBIDO))

    def test_solo_recibido_es_cancelable(self):
        self.assertTrue(Pedido(estado=Estado.RECIBIDO).puede_cancelarse)
        for estado in (Estado.EN_PREPARACION, Estado.LISTO, Estado.CANCELADO):
            self.assertFalse(Pedido(estado=estado).puede_cancelarse)

    def test_estado_invalido_rechazado_por_base_de_datos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.crear_pedido(estado="INVENTADO")

    def test_calcular_total_usa_precio_historico(self):
        pedido = self.crear_pedido()
        PedidoDetalle.objects.create(pedido=pedido, plato=self.plato1, cantidad=2,
                                     precio_unitario=self.plato1.precio)
        PedidoDetalle.objects.create(pedido=pedido, plato=self.plato2, cantidad=1,
                                     precio_unitario=self.plato2.precio)
        self.assertEqual(pedido.calcular_total(), Decimal("123455.00"))

        Plato.objects.filter(pk=self.plato1.pk).update(precio=Decimal("99999.00"))
        self.assertEqual(pedido.calcular_total(), Decimal("123455.00"))

    def test_total_de_pedido_sin_detalles_es_cero(self):
        self.assertEqual(self.crear_pedido().calcular_total(), Decimal("0.00"))

    def test_subtotal_detalle(self):
        detalle = PedidoDetalle(cantidad=3, precio_unitario=Decimal("1000.50"))
        self.assertEqual(detalle.subtotal, Decimal("3001.50"))

    def test_cantidad_detalle_debe_ser_positiva(self):
        pedido = self.crear_pedido()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PedidoDetalle.objects.create(pedido=pedido, plato=self.plato1, cantidad=0,
                                         precio_unitario=Decimal("1.00"))

    def test_plato_no_se_repite_en_un_pedido(self):
        pedido = self.crear_pedido()
        PedidoDetalle.objects.create(pedido=pedido, plato=self.plato1, cantidad=1,
                                     precio_unitario=Decimal("1.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            PedidoDetalle.objects.create(pedido=pedido, plato=self.plato1, cantidad=1,
                                         precio_unitario=Decimal("1.00"))

    def test_plato_con_pedidos_no_se_puede_borrar(self):
        from django.db.models import ProtectedError

        pedido = self.crear_pedido()
        PedidoDetalle.objects.create(pedido=pedido, plato=self.plato1, cantidad=1,
                                     precio_unitario=Decimal("1.00"))
        with self.assertRaises(ProtectedError):
            self.plato1.delete()

    def test_queryset_activos(self):
        recibido = self.crear_pedido()
        preparacion = self.crear_pedido(estado=Estado.EN_PREPARACION)
        self.crear_pedido(estado=Estado.LISTO)
        self.crear_pedido(estado=Estado.CANCELADO)
        self.assertEqual(set(Pedido.objects.activos()), {recibido, preparacion})

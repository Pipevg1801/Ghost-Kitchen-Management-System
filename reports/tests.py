from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.tests_utils import UsuariosPorRolMixin, crear_plato
from orders import services as pedidos
from orders.models import Pedido

from . import services

Estado = Pedido.Estado


class InformesTestBase(UsuariosPorRolMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plato1 = crear_plato("Ítem del menú #1", "12345.00", disponible=50)
        cls.plato2 = crear_plato("Ítem del menú #2", "98765.00", disponible=50)
        cls.p1 = pedidos.confirmar_pedido(cls.cliente, {cls.plato1.pk: 2})        # 24.690
        cls.p2 = pedidos.confirmar_pedido(cls.cliente2, {cls.plato2.pk: 1})       # 98.765
        cls.p3 = pedidos.confirmar_pedido(cls.cliente, {cls.plato1.pk: 1})        # 12.345 -> cancelado
        pedidos.cancelar_pedido(cls.p3.pk, cls.cliente)
        pedidos.cambiar_estado(cls.p2.pk, Estado.EN_PREPARACION)
        cls.antiguo = pedidos.confirmar_pedido(cls.cliente2, {cls.plato1.pk: 4})  # hace 10 días
        Pedido.objects.filter(pk=cls.antiguo.pk).update(
            fecha_creacion=timezone.now() - timedelta(days=10)
        )


class ServiciosInformesTests(InformesTestBase):
    def test_consolidado_de_hoy(self):
        resumen = services.resumen_consolidado("hoy")
        self.assertEqual(resumen["pedidos"], 2)
        self.assertEqual(resumen["ingresos"], Decimal("123455.00"))
        self.assertEqual(resumen["ticket_promedio"], Decimal("61727.50"))
        self.assertEqual(resumen["cancelados"], 1)

    def test_consolidado_por_periodo(self):
        self.assertEqual(services.resumen_consolidado("7d")["pedidos"], 2)
        self.assertEqual(services.resumen_consolidado("30d")["pedidos"], 3)
        self.assertEqual(services.resumen_consolidado("todo")["ingresos"], Decimal("172835.00"))

    def test_consolidado_sin_pedidos(self):
        Pedido.objects.all().delete()
        resumen = services.resumen_consolidado("hoy")
        self.assertEqual((resumen["pedidos"], resumen["ingresos"], resumen["ticket_promedio"]),
                         (0, Decimal("0.00"), Decimal("0.00")))

    def test_grafico_series_por_estado(self):
        datos = services.datos_grafico(14)
        self.assertEqual(len(datos["etiquetas"]), 14)
        self.assertEqual(datos["totales_por_estado"],
                         {"RECIBIDO": 2, "EN_PREPARACION": 1, "LISTO": 0, "CANCELADO": 1})
        self.assertEqual(datos["ingresos"][-1], 123455.0)
        recibidos = next(s for s in datos["series"] if s["estado"] == "RECIBIDO")["datos"]
        self.assertEqual(recibidos[-1], 1)
        self.assertEqual(recibidos[-11], 1)

    def test_grafico_rango_invalido_usa_7_dias(self):
        self.assertEqual(services.datos_grafico(999)["dias"], 7)

    def test_platos_mas_vendidos_excluye_cancelados(self):
        filas = services.platos_mas_vendidos("hoy")
        self.assertEqual({f["plato__nombre"]: f["unidades"] for f in filas},
                         {"Ítem del menú #1": 2, "Ítem del menú #2": 1})

    def test_filtrar_pedidos(self):
        self.assertEqual(list(services.filtrar_pedidos(estado=Estado.CANCELADO)), [self.p3])
        hoy = timezone.localdate()
        self.assertEqual(services.filtrar_pedidos(desde=hoy).count(), 3)
        self.assertEqual(services.filtrar_pedidos(hasta=hoy - timedelta(days=1)).count(), 1)
        self.assertEqual(services.filtrar_pedidos(cliente="felipe").count(), 2)


class VistasInformesTests(InformesTestBase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_dashboard(self):
        respuesta = self.client.get(reverse("reports:dashboard"))
        self.assertEqual(respuesta.status_code, 200)
        for texto in ("Gestión del menú", "Pedidos", "Informes", "$123.455"):
            self.assertContains(respuesta, texto)

    def test_informes_muestra_las_tres_secciones(self):
        respuesta = self.client.get(reverse("reports:informes"))
        for texto in ("Informe consolidado", "Informe gráfico", "Informe tabular", "Ticket promedio"):
            self.assertContains(respuesta, texto)

    def test_consolidado_con_periodo(self):
        respuesta = self.client.get(reverse("reports:consolidado"), {"periodo": "30d"})
        self.assertEqual(respuesta.context["resumen"]["pedidos"], 3)
        respuesta = self.client.get(reverse("reports:consolidado"), {"periodo": "invalido"})
        self.assertEqual(respuesta.context["resumen"]["periodo"], "hoy")

    def test_grafico_datos_json(self):
        respuesta = self.client.get(reverse("reports:grafico_datos"), {"dias": 30})
        datos = respuesta.json()
        self.assertEqual(datos["dias"], 30)
        self.assertEqual(sum(datos["totales_por_estado"].values()), 4)

    def test_tabular_filtra_y_pagina(self):
        respuesta = self.client.get(reverse("reports:tabular"), {"estado": Estado.EN_PREPARACION})
        self.assertEqual(list(respuesta.context["pedidos"]), [self.p2])
        self.assertContains(respuesta, "Felipe Vargas")
        self.assertContains(respuesta, "En preparación")
        self.assertEqual(respuesta.context["totales"]["suma"], Decimal("98765.00"))

    def test_tabular_paginacion(self):
        for _ in range(16):
            pedidos.confirmar_pedido(self.cliente, {self.plato1.pk: 1})
        respuesta = self.client.get(reverse("reports:tabular"))
        self.assertEqual(len(respuesta.context["pedidos"]), 15)
        self.assertTrue(respuesta.context["pagina"].has_next())
        segunda = self.client.get(reverse("reports:tabular"), {"page": 2})
        self.assertEqual(len(segunda.context["pedidos"]), 5)

    def test_tabular_rango_de_fechas_invalido(self):
        hoy = timezone.localdate()
        respuesta = self.client.get(reverse("reports:tabular"),
                                    {"desde": hoy.isoformat(), "hasta": (hoy - timedelta(days=2)).isoformat()})
        self.assertIn("hasta", respuesta.context["form"].errors)


class PermisosInformesTests(InformesTestBase):
    URLS = ("reports:dashboard", "reports:informes", "reports:consolidado",
            "reports:grafico", "reports:grafico_datos", "reports:tabular")

    def test_solo_administrador_accede(self):
        for usuario in (self.cliente, self.operario):
            self.client.force_login(usuario)
            for nombre in self.URLS:
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, (usuario, nombre))

    def test_anonimo_redirigido(self):
        for nombre in self.URLS:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 302)

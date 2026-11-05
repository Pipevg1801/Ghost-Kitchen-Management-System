from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from menu.models import Categoria, Plato
from orders.models import Pedido

from .tests import InformesTestBase


class InformeAPITests(InformesTestBase):
    def setUp(self):
        self.url = reverse("reports:api_informes")

    def entrar(self):
        self.client.force_login(self.admin)

    def test_sesion_requiere_rol_administrador(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["error"]["codigo"], "no_autenticado")
        for usuario in (self.cliente, self.operario):
            with self.subTest(usuario=usuario):
                self.client.force_login(usuario)
                respuesta = self.client.get(self.url)
                self.assertEqual(respuesta.status_code, 403)
                self.assertEqual(respuesta.json()["error"]["codigo"], "sin_permiso")

    @override_settings(REPORTS_API_TOKEN="token-sintetico-de-prueba")
    def test_bearer_funciona_sin_sesion_y_no_se_acepta_por_url(self):
        respuesta = self.client.get(
            self.url, headers={"Authorization": "Bearer token-sintetico-de-prueba"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["resumen"]["pedidos_totales"], 4)
        self.assertIn("no-store", respuesta["Cache-Control"])
        self.assertIn("Authorization", respuesta["Vary"])
        respuesta = self.client.get(self.url, {"token": "token-sintetico-de-prueba"})
        self.assertEqual(respuesta.status_code, 401)
        self.entrar()
        respuesta = self.client.get(self.url, headers={"Authorization": "Bearer equivocado"})
        self.assertEqual(respuesta.status_code, 401)

    @override_settings(REPORTS_API_TOKEN="")
    def test_bearer_vacio_desactiva_autenticacion_por_token(self):
        respuesta = self.client.get(self.url, headers={"Authorization": "Bearer "})
        self.assertEqual(respuesta.status_code, 401)

    def test_solo_lectura_incluso_con_sesion_y_sin_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        respuesta = cliente.post(self.url, {"estado": Pedido.Estado.CANCELADO})
        self.assertEqual(respuesta.status_code, 405)
        self.assertEqual(respuesta["Allow"], "GET")
        self.assertEqual(respuesta.json()["error"]["codigo"], "metodo_no_permitido")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.estado, Pedido.Estado.RECIBIDO)

    def test_exporta_totales_detalles_historicos_e_inventario(self):
        categoria = Categoria.objects.create(nombre="Archivo", slug="archivo", activa=False)
        Plato.objects.filter(pk=self.plato1.pk).update(
            precio=Decimal("15990.50"), categoria=categoria, activo=False,
        )
        self.entrar()
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["moneda"], "COP")
        self.assertEqual(datos["resumen"], {
            "pedidos": 3, "pedidos_totales": 4, "cancelados": 1, "activos": 3,
            "listos": 0, "ingresos": "172835.00", "ticket_promedio": "57611.67",
        })
        self.assertEqual(sum(fila["cantidad"] for fila in datos["por_estado"]), 4)
        self.assertEqual(sum(Decimal(dia["ingresos"]) for dia in datos["serie_diaria"]),
                         Decimal("172835.00"))
        ranking = {fila["plato_id"]: fila for fila in datos["platos_mas_vendidos"]}
        self.assertEqual(ranking[self.plato1.pk]["unidades"], 6)
        self.assertEqual(ranking[self.plato1.pk]["categoria_id"], categoria.pk)
        orden = next(fila for fila in datos["pedidos"] if fila["id"] == self.p1.pk)
        self.assertEqual(orden["detalles"][0]["precio_unitario"], "12345.00")
        self.assertEqual(orden["detalles"][0]["subtotal"], "24690.00")
        self.assertEqual(set(orden["cliente"]), {"id", "nombre"})
        plato = next(fila for fila in datos["inventario"]["platos"] if fila["id"] == self.plato1.pk)
        self.assertEqual(plato["precio"], "15990.50")
        self.assertFalse(plato["activo"])
        self.assertIn(categoria.pk, [fila["id"] for fila in datos["inventario"]["categorias"]])

    def test_filtros_de_fecha_local_cliente_y_estado(self):
        self.entrar()
        zona = ZoneInfo("America/Bogota")
        hoy = timezone.localdate()
        cerca_de_medianoche = datetime.combine(hoy, time(23, 59), tzinfo=zona)
        Pedido.objects.filter(pk=self.p3.pk).update(fecha_creacion=cerca_de_medianoche)
        filtros = {
            "desde": hoy.isoformat(), "hasta": hoy.isoformat(),
            "estado": Pedido.Estado.CANCELADO, "cliente": self.cliente.email,
        }
        datos = self.client.get(self.url, filtros).json()
        self.assertEqual([fila["id"] for fila in datos["pedidos"]], [self.p3.pk])
        self.assertEqual(datos["serie_diaria"][0]["fecha"], hoy.isoformat())
        self.assertEqual(datos["serie_diaria"][0]["ingresos"], "0.00")
        self.assertEqual(datos["resumen"]["pedidos"], 0)
        self.assertEqual(datos["platos_mas_vendidos"], [])

    def test_paginacion_estable_sin_recortar_los_agregados(self):
        self.entrar()
        Pedido.objects.update(fecha_creacion=timezone.now())
        primera = self.client.get(self.url, {"por_pagina": 2}).json()
        segunda = self.client.get(primera["paginacion"]["siguiente"]).json()
        ids = [fila["id"] for datos in (primera, segunda) for fila in datos["pedidos"]]
        self.assertEqual(ids, sorted([self.p1.pk, self.p2.pk, self.p3.pk, self.antiguo.pk],
                                    reverse=True))
        self.assertEqual(primera["resumen"], segunda["resumen"])
        self.assertEqual(primera["paginacion"]["total_pedidos"], 4)
        self.assertIsNone(segunda["paginacion"]["siguiente"])
        self.assertEqual(self.client.get(self.url, {"por_pagina": 2, "pagina": 3}).status_code, 404)

    def test_valida_filtros_y_devuelve_json_vacio_para_rangos_sin_pedidos(self):
        self.entrar()
        for parametros in ({"estado": "INEXISTENTE"}, {"por_pagina": 251}, {"pagina": 0},
                           {"desde": "ayer"}, {"desde": "2026-10-02", "hasta": "2026-10-01"},
                           {"desdee": "2026-10-02"}):
            with self.subTest(parametros=parametros):
                respuesta = self.client.get(self.url, parametros)
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.json()["error"]["codigo"], "filtros_invalidos")
        datos = self.client.get(self.url, {"hasta": "2000-01-01"}).json()
        self.assertEqual(datos["pedidos"], [])
        self.assertEqual(datos["resumen"]["ingresos"], "0.00")
        self.assertEqual(datos["paginacion"]["total_pedidos"], 0)
        self.assertTrue(datos["inventario"]["platos"])

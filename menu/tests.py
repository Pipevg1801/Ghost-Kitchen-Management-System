from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from core.tests_utils import UsuariosPorRolMixin, crear_plato
from orders.services import confirmar_pedido

from .models import Categoria, Plato


class PlatoModelTests(TestCase):
    def crear(self, **campos):
        datos = {"nombre": "Plato", "precio": Decimal("12345.00"), "cantidad_disponible": 5}
        datos.update(campos)
        return Plato.objects.create(**datos)

    def test_precio_se_guarda_como_decimal(self):
        plato = self.crear(precio=Decimal("12345.67"))
        plato.refresh_from_db()
        self.assertIsInstance(plato.precio, Decimal)
        self.assertEqual(plato.precio, Decimal("12345.67"))

    def test_precio_debe_ser_mayor_que_cero_en_validacion(self):
        with self.assertRaises(ValidationError):
            Plato(nombre="Gratis", precio=Decimal("0"), cantidad_disponible=1).full_clean()

    def test_precio_debe_ser_mayor_que_cero_en_base_de_datos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.crear(precio=Decimal("0"))

    def test_cantidades_no_negativas_en_base_de_datos(self):
        for campo in ("cantidad_disponible", "cantidad_reservada"):
            with self.subTest(campo=campo):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.crear(nombre=f"Negativo {campo}", **{campo: -1})

    def test_nombre_unico(self):
        self.crear()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.crear()

    def test_queryset_con_disponibilidad(self):
        self.crear(nombre="Disponible")
        self.crear(nombre="Agotado", cantidad_disponible=0)
        self.crear(nombre="Inactivo", activo=False)
        self.assertEqual(
            list(Plato.objects.con_disponibilidad().values_list("nombre", flat=True)),
            ["Disponible"],
        )


# --- Vistas del menú -------------------------------------------------------

DATOS_PLATO = {
    "nombre": "Ítem del menú #9", "precio": "15000.00", "descripcion": "Nuevo plato",
    "cantidad_disponible": 7, "cantidad_reservada": 0, "activo": "on",
}


class CatalogoViewTests(UsuariosPorRolMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.plato = crear_plato()
        cls.oculto = crear_plato(nombre="Plato oculto", activo=False)

    def test_cliente_consulta_platos_activos(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("menu:catalogo"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ítem del menú #1")
        self.assertContains(respuesta, "$12.345")
        self.assertContains(respuesta, "Agregar")
        self.assertNotContains(respuesta, "Plato oculto")

    def test_operario_consulta_menu_sin_boton_agregar(self):
        self.client.force_login(self.operario)
        respuesta = self.client.get(reverse("menu:catalogo"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, reverse("orders:carrito_agregar"))

    def test_busqueda(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("menu:catalogo"), {"q": "inexistente"})
        self.assertNotContains(respuesta, "Ítem del menú #1")


class RestaurantePublicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nombre="Bowls", slug="bowls")
        cls.plato = crear_plato(nombre="Bowl de prueba", categoria=cls.categoria)
        cls.otro = crear_plato(nombre="Pasta de prueba")
        cls.oculto = crear_plato(nombre="Producto oculto", activo=False)

    def test_escaparate_publica_solo_platos_activos(self):
        respuesta = self.client.get(reverse("menu:restaurante"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.plato.nombre)
        self.assertNotContains(respuesta, self.oculto.nombre)
        self.assertNotContains(respuesta, reverse("orders:carrito_agregar"))

    def test_categoria_y_busqueda_se_combinan(self):
        respuesta = self.client.get(reverse("menu:restaurante"), {"categoria": "bowls", "q": "prueba"})
        self.assertEqual(list(respuesta.context["platos"]), [self.plato])
        respuesta = self.client.get(reverse("menu:restaurante"), {"categoria": "bowls", "q": "Pasta"})
        self.assertFalse(respuesta.context["platos"].exists())

    def test_ver_menu_no_autoriza_pedidos_anonimos(self):
        respuesta = self.client.post(reverse("orders:carrito_agregar"), {"plato_id": self.plato.pk, "cantidad": 1})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.url.startswith(reverse("accounts:login")))
        self.assertNotIn("carrito", self.client.session)


class GestionMenuViewTests(UsuariosPorRolMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_crear_plato(self):
        respuesta = self.client.post(reverse("menu:admin_crear"), DATOS_PLATO, follow=True)
        self.assertContains(respuesta, "Producto creado correctamente.")
        plato = Plato.objects.get(nombre="Ítem del menú #9")
        self.assertEqual(plato.precio, Decimal("15000.00"))
        self.assertEqual(plato.cantidad_disponible, 7)

    def test_modificar_plato(self):
        plato = crear_plato()
        datos = {**DATOS_PLATO, "nombre": "Renombrado", "precio": "20000", "cantidad_reservada": 2}
        respuesta = self.client.post(reverse("menu:admin_editar", args=[plato.pk]), datos, follow=True)
        self.assertContains(respuesta, "Producto actualizado.")
        plato.refresh_from_db()
        self.assertEqual((plato.nombre, plato.precio, plato.cantidad_reservada),
                         ("Renombrado", Decimal("20000.00"), 2))

    def test_validar_precio_mayor_que_cero(self):
        for precio in ("0", "-5"):
            respuesta = self.client.post(reverse("menu:admin_crear"), {**DATOS_PLATO, "precio": precio})
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn("precio", respuesta.context["form"].errors)
        self.assertFalse(Plato.objects.filter(nombre="Ítem del menú #9").exists())

    def test_validar_disponibilidad_no_negativa(self):
        for campo in ("cantidad_disponible", "cantidad_reservada"):
            respuesta = self.client.post(reverse("menu:admin_crear"), {**DATOS_PLATO, campo: -1})
            self.assertIn(campo, respuesta.context["form"].errors)

    def test_nombre_obligatorio_y_unico(self):
        crear_plato(nombre="Existente")
        respuesta = self.client.post(reverse("menu:admin_crear"), {**DATOS_PLATO, "nombre": "  "})
        self.assertIn("nombre", respuesta.context["form"].errors)
        respuesta = self.client.post(reverse("menu:admin_crear"), {**DATOS_PLATO, "nombre": "existente"})
        self.assertIn("nombre", respuesta.context["form"].errors)

    def test_lista_muestra_tabla(self):
        crear_plato()
        respuesta = self.client.get(reverse("menu:admin_lista"))
        for texto in ("Cantidad disponible", "Cantidad reservada", "Editar", "Eliminar", "Agregar producto"):
            self.assertContains(respuesta, texto)

    def test_eliminar_plato_sin_pedidos_lo_borra(self):
        plato = crear_plato()
        self.client.post(reverse("menu:admin_eliminar", args=[plato.pk]))
        self.assertFalse(Plato.objects.filter(pk=plato.pk).exists())

    def test_eliminar_plato_con_pedidos_lo_oculta(self):
        plato = crear_plato()
        confirmar_pedido(self.cliente, {plato.pk: 1})
        self.client.post(reverse("menu:admin_eliminar", args=[plato.pk]))
        plato.refresh_from_db()
        self.assertFalse(plato.activo)

    def test_eliminar_requiere_post(self):
        plato = crear_plato()
        self.assertEqual(self.client.get(reverse("menu:admin_eliminar", args=[plato.pk])).status_code, 405)


class PermisosMenuTests(UsuariosPorRolMixin, TestCase):
    def test_cliente_y_operario_no_gestionan_menu(self):
        plato = crear_plato()
        urls = [
            reverse("menu:admin_lista"), reverse("menu:admin_crear"),
            reverse("menu:admin_editar", args=[plato.pk]),
        ]
        for usuario in (self.cliente, self.operario):
            self.client.force_login(usuario)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403, (usuario, url))
            self.assertEqual(self.client.post(reverse("menu:admin_crear"), DATOS_PLATO).status_code, 403)
            self.assertEqual(
                self.client.post(reverse("menu:admin_eliminar", args=[plato.pk])).status_code, 403
            )
        self.assertTrue(Plato.objects.filter(pk=plato.pk).exists())

    def test_administrador_no_usa_catalogo_de_cliente(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("menu:catalogo")).status_code, 403)


class ImagenPlatoTests(UsuariosPorRolMixin, TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.configuracion = self.settings(MEDIA_ROOT=self.media.name)
        self.configuracion.enable()
        self.addCleanup(self.configuracion.disable)
        self.client.force_login(self.admin)

    def test_editar_producto_conserva_imagen_y_catalogo_la_muestra(self):
        archivo = BytesIO()
        Image.new("RGB", (20, 20), "orange").save(archivo, format="PNG")
        datos = {**DATOS_PLATO, "imagen": SimpleUploadedFile("plato.png", archivo.getvalue(), content_type="image/png")}
        self.client.post(reverse("menu:admin_crear"), datos)
        plato = Plato.objects.get(nombre=DATOS_PLATO["nombre"])
        imagen_original = plato.imagen.name

        respuesta = self.client.post(reverse("menu:admin_editar", args=[plato.pk]), {**DATOS_PLATO, "precio": "16000"})
        self.assertEqual(respuesta.status_code, 302)
        plato.refresh_from_db()
        self.assertEqual(plato.imagen.name, imagen_original)
        self.assertEqual(plato.precio, Decimal("16000"))
        self.client.force_login(self.cliente)
        self.assertContains(self.client.get(reverse("menu:catalogo")), plato.imagen.url)

    def test_rechaza_archivo_que_no_es_imagen(self):
        archivo = SimpleUploadedFile("plato.txt", b"no es una imagen", content_type="text/plain")
        respuesta = self.client.post(reverse("menu:admin_crear"), {**DATOS_PLATO, "imagen": archivo})
        self.assertIn("imagen", respuesta.context["form"].errors)
        self.assertFalse(Plato.objects.filter(nombre=DATOS_PLATO["nombre"]).exists())

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.views import View

from .forms import RegistroForm
from .models import Rol, Usuario
from .permissions import (
    AdministradorRequeridoMixin,
    administrador_requerido,
    cliente_requerido,
    operario_requerido,
)

PASSWORD = "ClaveSegura#2026"


def crear_usuario(email, rol_nombre, **extra):
    return Usuario.objects.create_user(
        email=email, password=PASSWORD, nombre=extra.pop("nombre", email.split("@")[0]),
        rol=Rol.objects.get(nombre=rol_nombre), **extra,
    )


class UsuariosBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = crear_usuario("cliente@test.com", Rol.Nombre.CLIENTE)
        cls.operario = crear_usuario("operario@test.com", Rol.Nombre.OPERARIO)
        cls.admin = crear_usuario("admin@test.com", Rol.Nombre.ADMINISTRADOR)


class RolesYUsuariosTests(UsuariosBaseTestCase):
    def test_migracion_crea_los_tres_roles(self):
        self.assertEqual(
            set(Rol.objects.values_list("nombre", flat=True)),
            {"Cliente", "Operario", "Administrador"},
        )

    def test_roles_son_distintos(self):
        self.assertTrue(self.cliente.es_cliente)
        self.assertFalse(self.cliente.es_operario or self.cliente.es_administrador)
        self.assertTrue(self.operario.es_operario)
        self.assertFalse(self.operario.es_cliente or self.operario.es_administrador)
        self.assertTrue(self.admin.es_administrador)
        self.assertFalse(self.admin.es_cliente or self.admin.es_operario)

    def test_password_se_guarda_hasheada(self):
        self.assertNotEqual(self.cliente.password, PASSWORD)
        self.assertTrue(self.cliente.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(self.cliente.check_password(PASSWORD))

    def test_email_se_normaliza_en_minusculas(self):
        usuario = crear_usuario("Mixto@Test.COM", Rol.Nombre.CLIENTE)
        self.assertEqual(usuario.email, "mixto@test.com")

    def test_create_user_asigna_rol_cliente_por_defecto(self):
        usuario = Usuario.objects.create_user(email="nuevo@test.com", password=PASSWORD, nombre="N")
        self.assertTrue(usuario.es_cliente)

    def test_create_superuser_asigna_rol_administrador(self):
        usuario = Usuario.objects.create_superuser(email="su@test.com", password=PASSWORD, nombre="S")
        self.assertTrue(usuario.es_administrador)
        self.assertTrue(usuario.is_superuser and usuario.is_staff)

    def test_solo_administrador_es_staff(self):
        self.assertFalse(self.cliente.is_staff)
        self.assertFalse(self.operario.is_staff)
        self.assertTrue(self.admin.is_staff)


class LoginTests(UsuariosBaseTestCase):
    def test_login_correcto_redirige(self):
        respuesta = self.client.post(
            reverse("accounts:login"), {"username": "cliente@test.com", "password": PASSWORD}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.cliente.pk)

    def test_login_es_insensible_a_mayusculas_en_email(self):
        self.client.post(reverse("accounts:login"),
                         {"username": "CLIENTE@test.com", "password": PASSWORD})
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_incorrecto(self):
        respuesta = self.client.post(
            reverse("accounts:login"), {"username": "cliente@test.com", "password": "incorrecta"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_usuario_inactivo_rechazado(self):
        crear_usuario("inactivo@test.com", Rol.Nombre.CLIENTE, is_active=False)
        self.client.post(reverse("accounts:login"),
                         {"username": "inactivo@test.com", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_por_post(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(respuesta, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class AccesoNoAutorizadoTests(UsuariosBaseTestCase):
    def test_anonimo_redirigido_a_login(self):
        for nombre_url in ("accounts:inicio", "accounts:perfil"):
            respuesta = self.client.get(reverse(nombre_url))
            self.assertRedirects(
                respuesta, f"{reverse('accounts:login')}?next={reverse(nombre_url)}",
                fetch_redirect_response=False,
            )

    def test_middleware_protege_rutas_inexistentes_y_futuras(self):
        respuesta = self.client.get("/admin-panel/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.url.startswith(reverse("accounts:login")))

    def test_login_y_registro_son_publicos(self):
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:registro")).status_code, 200)


class PermisosPorRolTests(UsuariosBaseTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _ejecutar(self, vista, usuario):
        request = self.factory.get("/protegida/")
        request.user = usuario
        return vista(request)

    def test_decoradores_permiten_solo_su_rol(self):
        vista_ok = lambda request: HttpResponse("ok")  # noqa: E731
        casos = {
            cliente_requerido(vista_ok): self.cliente,
            operario_requerido(vista_ok): self.operario,
            administrador_requerido(vista_ok): self.admin,
        }
        todos = (self.cliente, self.operario, self.admin)
        for vista, permitido in casos.items():
            for usuario in todos:
                if usuario == permitido:
                    self.assertEqual(self._ejecutar(vista, usuario).status_code, 200)
                else:
                    with self.assertRaises(PermissionDenied):
                        self._ejecutar(vista, usuario)

    def test_mixin_administrador_rechaza_cliente_y_operario(self):
        class VistaAdmin(AdministradorRequeridoMixin, View):
            def get(self, request):
                return HttpResponse("ok")

        vista = VistaAdmin.as_view()
        self.assertEqual(self._ejecutar(vista, self.admin).status_code, 200)
        for usuario in (self.cliente, self.operario):
            with self.assertRaises(PermissionDenied):
                self._ejecutar(vista, usuario)


class RegistroTests(TestCase):
    datos = {
        "nombre": "Juan Serrano", "email": "juan@test.com", "telefono": "3001112233",
        "direccion": "Calle 1 # 2-3", "password1": PASSWORD, "password2": PASSWORD,
    }

    def test_registro_crea_cliente_e_inicia_sesion(self):
        respuesta = self.client.post(reverse("accounts:registro"), self.datos)
        self.assertEqual(respuesta.status_code, 302)
        usuario = Usuario.objects.get(email="juan@test.com")
        self.assertTrue(usuario.es_cliente)
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_email_duplicado_rechazado(self):
        crear_usuario("juan@test.com", Rol.Nombre.CLIENTE)
        form = RegistroForm(data={**self.datos, "email": "JUAN@test.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_invalido_rechazado(self):
        form = RegistroForm(data={**self.datos, "email": "no-es-email"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_debil_rechazada(self):
        form = RegistroForm(data={**self.datos, "password1": "12345678", "password2": "12345678"})
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_passwords_distintas_rechazadas(self):
        form = RegistroForm(data={**self.datos, "password2": "OtraClave#2026"})
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_campos_obligatorios(self):
        form = RegistroForm(data={})
        self.assertFalse(form.is_valid())
        for campo in ("nombre", "email", "telefono", "direccion", "password1", "password2"):
            self.assertIn(campo, form.errors)

    def test_registro_no_permite_elegir_rol(self):
        admin = Rol.objects.get(nombre=Rol.Nombre.ADMINISTRADOR)
        self.client.post(reverse("accounts:registro"), {**self.datos, "rol": admin.pk})
        self.assertTrue(Usuario.objects.get(email="juan@test.com").es_cliente)


class PerfilTests(UsuariosBaseTestCase):
    def test_actualiza_solo_el_usuario_autenticado(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse("accounts:perfil"),
                         {"nombre": "Nuevo Nombre", "telefono": "3000000000", "direccion": "X"})
        self.cliente.refresh_from_db()
        self.operario.refresh_from_db()
        self.assertEqual(self.cliente.nombre, "Nuevo Nombre")
        self.assertEqual(self.operario.nombre, "operario")

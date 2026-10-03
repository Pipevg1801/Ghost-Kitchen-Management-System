from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.navegacion import url_inicio

from .forms import LoginForm, PerfilForm, RegistroForm


class IniciarSesionView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return url_inicio(self.request.user)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Bienvenido, {self.request.user.get_short_name()}.")
        return respuesta


class CerrarSesionView(LogoutView):
    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        messages.info(request, "Sesión cerrada correctamente.")
        return respuesta


@require_http_methods(["GET", "POST"])
def registro(request):
    if request.user.is_authenticated:
        return redirect(url_inicio(request.user))
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Cuenta creada correctamente. ¡Bienvenido!")
        return redirect(url_inicio(usuario))
    return render(request, "accounts/registro.html", {"form": form})


@login_required
def inicio(request):
    return redirect(url_inicio(request.user))


@login_required
@require_http_methods(["GET", "POST"])
def perfil(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado.")
        return redirect("accounts:perfil")
    return render(request, "accounts/perfil.html", {"form": form})

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.IniciarSesionView.as_view(), name="login"),
    path("logout/", views.CerrarSesionView.as_view(), name="logout"),
    path("registro/", views.registro, name="registro"),
    path("perfil/", views.perfil, name="perfil"),
]

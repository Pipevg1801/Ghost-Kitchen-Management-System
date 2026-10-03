from django.urls import path

from . import views

app_name = "menu"

urlpatterns = [
    path("menu/", views.catalogo, name="catalogo"),
    path("admin-panel/menu/", views.PlatoListaView.as_view(), name="admin_lista"),
    path("admin-panel/menu/agregar/", views.PlatoCrearView.as_view(), name="admin_crear"),
    path("admin-panel/menu/<int:pk>/editar/", views.PlatoEditarView.as_view(), name="admin_editar"),
    path("admin-panel/menu/<int:pk>/eliminar/", views.plato_eliminar, name="admin_eliminar"),
]

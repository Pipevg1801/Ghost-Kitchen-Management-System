from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    # Carrito del cliente
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/agregar/", views.carrito_agregar, name="carrito_agregar"),
    path("carrito/modificar/", views.carrito_modificar, name="carrito_modificar"),
    path("carrito/eliminar/", views.carrito_eliminar, name="carrito_eliminar"),
    path("carrito/cancelar/", views.carrito_cancelar, name="carrito_cancelar"),
    path("pedido/confirmar/", views.pedido_confirmar, name="pedido_confirmar"),
    # Pedidos del cliente
    path("pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("pedidos/<int:pk>/", views.pedido_detalle, name="pedido_detalle"),
    path("pedidos/<int:pk>/cancelar/", views.pedido_cancelar, name="pedido_cancelar"),
    # Panel del operario
    path("operario/pedidos/", views.operario_pedidos, name="operario_pedidos"),
    path("operario/pedidos/<int:pk>/estado/", views.operario_cambiar_estado,
         name="operario_cambiar_estado"),
]

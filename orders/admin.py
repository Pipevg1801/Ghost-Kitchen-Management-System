from django.contrib import admin

from .models import Pedido, PedidoDetalle


class PedidoDetalleInline(admin.TabularInline):
    model = PedidoDetalle
    extra = 0
    readonly_fields = ("plato", "cantidad", "precio_unitario")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "estado", "total", "fecha_creacion")
    list_filter = ("estado", "fecha_creacion")
    search_fields = ("id", "usuario__nombre", "usuario__email")
    readonly_fields = ("usuario", "total", "fecha_creacion")
    inlines = [PedidoDetalleInline]

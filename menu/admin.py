from django.contrib import admin

from .models import Categoria, Plato


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activa")
    list_editable = ("orden", "activa")
    prepopulated_fields = {"slug": ("nombre",)}
    search_fields = ("nombre", "descripcion")


@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "categoria",
        "precio",
        "cantidad_disponible",
        "cantidad_reservada",
        "activo",
    )
    list_filter = ("categoria", "activo")
    search_fields = ("nombre", "descripcion")
    list_editable = ("precio", "cantidad_disponible", "activo")
    list_select_related = ("categoria",)
    fieldsets = (
        (None, {
            "fields": ("nombre", "descripcion", "categoria", "imagen")
        }),
        ("Precio e inventario", {
            "fields": ("precio", "cantidad_disponible", "cantidad_reservada", "activo")
        }),
    )
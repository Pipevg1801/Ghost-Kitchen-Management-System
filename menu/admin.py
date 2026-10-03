from django.contrib import admin

from .models import Plato


@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "cantidad_disponible", "cantidad_reservada", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)

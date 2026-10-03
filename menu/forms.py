from decimal import Decimal

from django import forms

from core.forms import BootstrapFormMixin

from .models import Plato


class PlatoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Plato
        fields = ("nombre", "precio", "descripcion", "cantidad_disponible", "cantidad_reservada", "activo")
        labels = {"activo": "Visible en el menú"}
        widgets = {
            "nombre": forms.TextInput(attrs={"maxlength": 120, "required": True}),
            "precio": forms.NumberInput(attrs={"min": "0.01", "step": "0.01", "required": True}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "cantidad_disponible": forms.NumberInput(attrs={"min": 0, "step": 1, "required": True}),
            "cantidad_reservada": forms.NumberInput(attrs={"min": 0, "step": 1, "required": True}),
        }

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        repetidos = Plato.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise forms.ValidationError("Ya existe un plato con este nombre.")
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio is None or precio <= Decimal("0"):
            raise forms.ValidationError("El precio debe ser mayor que cero.")
        return precio

    def _no_negativa(self, campo):
        valor = self.cleaned_data[campo]
        if valor is None or valor < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return valor

    def clean_cantidad_disponible(self):
        return self._no_negativa("cantidad_disponible")

    def clean_cantidad_reservada(self):
        return self._no_negativa("cantidad_reservada")

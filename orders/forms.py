from django import forms

from .models import Pedido


class AgregarCarritoForm(forms.Form):
    plato_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    cantidad = forms.IntegerField(min_value=1, max_value=99, initial=1)


class ModificarCarritoForm(forms.Form):
    INCREMENTAR = "incrementar"
    DISMINUIR = "disminuir"

    plato_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    accion = forms.ChoiceField(choices=((INCREMENTAR, "Incrementar"), (DISMINUIR, "Disminuir")))


class EliminarDelCarritoForm(forms.Form):
    plato_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput)


class CambiarEstadoForm(forms.Form):
    """El valor se valida contra el flujo en services.cambiar_estado."""

    estado = forms.ChoiceField(choices=Pedido.Estado.choices)

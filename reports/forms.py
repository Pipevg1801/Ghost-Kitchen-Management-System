from django import forms

from core.forms import BootstrapFormMixin
from orders.models import Pedido

from .services import PERIODOS


class FechaInput(forms.DateInput):
    """<input type="date"> exige el formato ISO en su valor."""

    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class PeriodoForm(BootstrapFormMixin, forms.Form):
    periodo = forms.ChoiceField(
        choices=[(clave, etiqueta) for clave, (etiqueta, _) in PERIODOS.items()],
        required=False,
    )

    def periodo_elegido(self):
        if not self.is_valid():
            return "hoy"
        return self.cleaned_data.get("periodo") or "hoy"


class FiltroPedidosForm(BootstrapFormMixin, forms.Form):
    estado = forms.ChoiceField(
        choices=[("", "Todos los estados"), *Pedido.Estado.choices], required=False
    )
    desde = forms.DateField(required=False, widget=FechaInput)
    hasta = forms.DateField(required=False, widget=FechaInput)
    cliente = forms.CharField(
        required=False, max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Nombre o correo"}),
    )

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and desde > hasta:
            self.add_error("hasta", "La fecha final debe ser posterior a la inicial.")
        return datos

    def filtros(self):
        if not self.is_valid():
            return {}
        return {clave: valor for clave, valor in self.cleaned_data.items() if valor}

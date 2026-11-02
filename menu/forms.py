from decimal import Decimal

from django import forms

from core.forms import BootstrapFormMixin

from .models import Categoria, Plato


class PlatoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Plato
        fields = (
            "nombre",
            "precio",
            "descripcion",
            "categoria",     # 👈 nuevo
            "imagen",        # 👈 nuevo
            "cantidad_disponible",
            "cantidad_reservada",
            "activo",
        )
        labels = {
            "activo": "Visible en el menú",
            "categoria": "Categoría",
            "imagen": "Imagen del plato",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"maxlength": 120, "required": True}),
            "precio": forms.NumberInput(attrs={"min": "0.01", "step": "0.01", "required": True}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "cantidad_disponible": forms.NumberInput(attrs={"min": 0, "step": 1, "required": True}),
            "cantidad_reservada": forms.NumberInput(attrs={"min": 0, "step": 1, "required": True}),
            "imagen": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar categorías activas, ordenadas igual que en el menú
        self.fields["categoria"].queryset = Categoria.objects.activas().order_by("orden", "nombre")
        self.fields["categoria"].empty_label = "— Sin categoría —"
        # Ayuda visual si ya hay imagen cargada
        if self.instance and self.instance.pk and self.instance.imagen:
            self.fields["imagen"].help_text = "Deja vacío para conservar la imagen actual."

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

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        # Solo validar si es un archivo nuevo (no un FieldFile existente)
        if imagen and hasattr(imagen, "size"):
            if imagen.size > 2 * 1024 * 1024:
                raise forms.ValidationError("La imagen no puede superar los 2 MB.")
            if not imagen.content_type.startswith("image/"):
                raise forms.ValidationError("El archivo debe ser una imagen (JPG, PNG, WEBP).")
        return imagen

    def _no_negativa(self, campo):
        valor = self.cleaned_data[campo]
        if valor is None or valor < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return valor

    def clean_cantidad_disponible(self):
        return self._no_negativa("cantidad_disponible")

    def clean_cantidad_reservada(self):
        return self._no_negativa("cantidad_reservada")
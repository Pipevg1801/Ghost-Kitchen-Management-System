from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from core.forms import BootstrapFormMixin

from .models import Rol, Usuario


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email",
                                       "placeholder": "correo@ejemplo.com"}),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Esta cuenta está inactiva.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class RegistroForm(BootstrapFormMixin, forms.ModelForm):
    """Registro público: siempre crea usuarios con rol Cliente."""

    password1 = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": 8}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": 8}),
    )

    class Meta:
        model = Usuario
        fields = ("nombre", "email", "telefono", "direccion")
        widgets = {
            "nombre": forms.TextInput(attrs={"autocomplete": "name", "maxlength": 150}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "telefono": forms.TextInput(attrs={"autocomplete": "tel", "pattern": r"[0-9+\s\-]{7,20}"}),
            "direccion": forms.TextInput(attrs={"autocomplete": "street-address"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("nombre", "email", "telefono", "direccion"):
            self.fields[campo].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return email

    def clean(self):
        datos = super().clean()
        password1 = datos.get("password1")
        password2 = datos.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if password1:
            usuario_temporal = Usuario(email=datos.get("email", ""), nombre=datos.get("nombre", ""))
            try:
                password_validation.validate_password(password1, usuario_temporal)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Rol.objects.get(nombre=Rol.Nombre.CLIENTE)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


class PerfilForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("nombre", "telefono", "direccion")
        widgets = {
            "telefono": forms.TextInput(attrs={"pattern": r"[0-9+\s\-]{7,20}"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nombre"].required = True

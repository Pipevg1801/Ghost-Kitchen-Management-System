from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import Rol, Usuario


class UsuarioCreacionAdminForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ("email", "nombre", "rol", "telefono", "direccion")

    def clean_password2(self):
        p1, p2 = self.cleaned_data.get("password1"), self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return p2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


class UsuarioCambioAdminForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Contraseña")

    class Meta:
        model = Usuario
        fields = "__all__"


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioCambioAdminForm
    add_form = UsuarioCreacionAdminForm
    list_display = ("email", "nombre", "rol", "is_active", "fecha_creacion")
    list_filter = ("rol", "is_active")
    search_fields = ("email", "nombre")
    ordering = ("nombre",)
    readonly_fields = ("fecha_creacion", "last_login")
    filter_horizontal = ()
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombre", "telefono", "direccion")}),
        ("Acceso", {"fields": ("rol", "is_active", "is_superuser")}),
        ("Fechas", {"fields": ("fecha_creacion", "last_login")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": (
            "email", "nombre", "rol", "telefono", "direccion", "password1", "password2",
        )}),
    )

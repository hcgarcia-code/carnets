from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import PerfilSindicato


class RegistroSindicatoForm(UserCreationForm):
    nombre_identificativo = forms.CharField(
        max_length=255,
        label="Sindicato o rama",
        help_text="Para que el administrador sepa a quién aprobar la cuenta.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        # Inactiva hasta que un administrador la revisa y la aprueba a mano:
        # este formulario es público (sin login), así que sin este cierre
        # cualquiera podría empezar a cargar datos de afiliación sindical sin
        # supervisión alguna.
        usuario.is_active = False
        if commit:
            usuario.save()
            PerfilSindicato.objects.create(
                usuario=usuario,
                nombre_identificativo=self.cleaned_data["nombre_identificativo"],
            )
        return usuario

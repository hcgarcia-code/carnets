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
    # Obligatorio a propósito. Django lo define opcional en el modelo User, y
    # dejarlo así significaría que una parte de las cuentas se queda sin vía de
    # recuperación de contraseña, sin saber cuáles hasta que alguien la
    # necesita. Es también la única forma de avisar a un sindicato de algo.
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        help_text="Necesario para poder recuperar la contraseña y para avisarte.",
    )
    persona_contacto = forms.CharField(
        max_length=255,
        label="Persona que solicita el alta",
        help_text="Quién eres, para que el administrador sepa a quién está aprobando.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.email = self.cleaned_data["email"]
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
                persona_contacto=self.cleaned_data["persona_contacto"],
            )
        return usuario

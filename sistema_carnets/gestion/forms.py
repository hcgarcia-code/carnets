import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import PerfilSindicato

# DNI (8 dígitos + letra) y NIE (X/Y/Z + 7 dígitos + letra). No se comprueba que
# la letra de control sea la correcta a propósito: aquí no se trata de validar un
# documento, sino de reconocer que alguien está poniendo uno donde no debe.
DOCUMENTO_DE_IDENTIDAD = re.compile(r'^(\d{8}|[XYZxyz]\d{7})[A-Za-z]$')


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

    def clean_username(self):
        """El nombre de usuario acaba en el registro de auditoría.

        Cada acción registrada (`login.correcto`, `afiliados.cargados`…) lleva
        el campo `usuario`. Si ese nombre es un DNI, una línea del registro pasa
        a decir que el titular de un documento concreto ha cargado afiliación
        sindical: dato de categoría especial (Art. 9) dentro de un archivo que
        el proyecto declara libre de datos personales, y que además se envía a
        un destino externo.

        Se valida aquí, en el formulario, y no en el modelo, para poder explicar
        el motivo a quien lo está escribiendo. El alta es autoservicio y pública:
        sin esto vuelve a pasar.
        """
        username = self.cleaned_data["username"]

        if DOCUMENTO_DE_IDENTIDAD.match(username):
            raise forms.ValidationError(
                "No uses un documento de identidad como nombre de usuario. Esta "
                "cuenta es del sindicato, no de una persona: pon algo que lo "
                "identifique a él (por ejemplo, «cgt_sov_avila»).",
            )

        return username

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

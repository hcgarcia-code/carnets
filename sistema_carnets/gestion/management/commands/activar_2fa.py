"""Da de alta el segundo factor de una cuenta del admin.

Sin este comando, activar el segundo factor equivaldria a cerrar el admin con
llave y tirarla: Django no trae ninguna pantalla para enrolar el primer
dispositivo, y sin dispositivo no se entra. Se ejecuta desde la consola del
servidor, asi que siempre hay una via de vuelta aunque nadie pueda entrar por
la web.

Tambien es la salida cuando alguien pierde el telefono: reejecutarlo revoca el
dispositivo anterior y emite uno nuevo.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice

NOMBRE_DISPOSITIVO = "principal"


class Command(BaseCommand):
    help = "Da de alta (o renueva) el segundo factor de una cuenta del admin."

    def add_arguments(self, parser):
        parser.add_argument("usuario", help="Nombre de usuario de la cuenta.")

    def handle(self, *args, **opciones):
        nombre = opciones["usuario"]
        try:
            usuario = User.objects.get(username=nombre)
        except User.DoesNotExist as exc:
            raise CommandError(f"El usuario {nombre!r} no existe.") from exc

        # Se borra el anterior en vez de anadir otro: si se acumularan, un
        # telefono perdido seguiria dando acceso indefinidamente.
        revocados, _ = TOTPDevice.objects.filter(user=usuario).delete()

        dispositivo = TOTPDevice.objects.create(
            user=usuario, name=NOMBRE_DISPOSITIVO, confirmed=True,
        )

        # Solo ASCII: la consola de Windows usa cp1252 y un caracter fuera de
        # ese juego abortaria el comando con UnicodeEncodeError despues de
        # haber creado ya el dispositivo, dejando al operador sin el secreto
        # de un dispositivo que si existe. Hay una prueba que lo comprueba.
        escribir = self.stdout.write
        if revocados:
            escribir(self.style.WARNING(
                f"Revocado(s) {revocados} dispositivo(s) anterior(es) de {nombre}.",
            ))

        escribir(self.style.SUCCESS(f"\nSegundo factor activado para {nombre}.\n"))
        escribir("Da de alta la cuenta en tu aplicacion de autenticacion")
        escribir("(Google Authenticator, Aegis, 1Password, Bitwarden...):\n")
        escribir(f"    Secreto:  {dispositivo.bin_key.hex()}")
        escribir(f"    O pega esta URL:\n    {dispositivo.config_url}\n")
        escribir(
            "A partir de ahora el admin pide un codigo de 6 digitos ademas de\n"
            "la contrasena. El login de sindicatos no cambia.\n",
        )

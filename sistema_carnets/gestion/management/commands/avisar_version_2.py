"""Avisa a los sindicatos de que el sistema pasa a la version 2.0.

Un envio a todo el censo tiene dos formas de salir mal que no se ven hasta que
ya ha salido:

1. Meter a todos los destinatarios en el mismo mensaje. Cada sindicato veria la
   lista completa de los demas, con sus direcciones: quien esta usando el
   sistema de carnets de CGT. Eso no es un descuido de estilo, es una
   comunicacion de datos a terceros que nadie ha autorizado. Por eso este
   comando compone un mensaje por destinatario y nunca usa copia ni copia
   oculta.

2. Enviarlo antes de tiempo. Por eso el modo por defecto es en seco: sin
   `--enviar` no sale nada, solo dice a quien escribiria.

No lleva control de "ya enviado": si se ejecuta dos veces, escribe dos veces.
Es una operacion de una sola vez y guardar ese estado costaria una migracion
para algo que se usa un dia. Mira la salida en seco antes de enviar.
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage, get_connection
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string

from gestion.auditoria import ACCIONES, registrar
from gestion.views import GRUPO_IMPRENTA

PLANTILLA_ASUNTO = 'gestion/correo/version_2_asunto.txt'
PLANTILLA_CUERPO = 'gestion/correo/version_2.txt'

# La direccion nueva del sistema. Se puede cambiar con --url; esta aqui como
# valor por defecto para que el modo en seco enseñe el mensaje real.
URL_POR_DEFECTO = 'https://carnetscgt.eu.pythonanywhere.com'

REMITENTE_DE_DJANGO = 'webmaster@localhost'


class Command(BaseCommand):
    help = "Avisa por correo a los sindicatos del paso a la version 2.0."

    def add_arguments(self, parser):
        parser.add_argument(
            "--enviar", action="store_true",
            help="Envia de verdad. Sin esto solo dice a quien escribiria.",
        )
        parser.add_argument(
            "--url", default=URL_POR_DEFECTO,
            help=f"Direccion nueva del sistema (por defecto {URL_POR_DEFECTO}).",
        )

    def handle(self, *args, **opciones):
        destinatarios, sin_correo = self._censo()

        self._informar_del_censo(destinatarios, sin_correo)

        if not opciones["enviar"]:
            self.stdout.write(self.style.WARNING(
                "\nEN SECO: no se ha enviado nada. Repite con --enviar cuando lo veas bien.",
            ))
            self._enseñar_una_muestra(destinatarios, opciones["url"])
            return

        if not destinatarios:
            self.stdout.write("No hay a quien escribir.")
            return

        self._comprobar_que_el_correo_saldra()
        enviados = self._enviar(destinatarios, opciones["url"])

        # Sin direcciones: este registro sale del ambito cifrado y guarda el
        # recuento, no a quien se escribio.
        registrar(ACCIONES.AVISO_ENVIADO, usuario="avisar_version_2", cantidad=enviados)

        self.stdout.write(self.style.SUCCESS(f"\nEnviados {enviados} mensajes."))

    # --- Quien recibe ---

    def _censo(self):
        """Sindicatos activos. Fuera la imprenta, el personal y los pendientes.

        La imprenta queda fuera porque el aviso habla de subir archivos y de la
        plantilla, que no es su trabajo. Las cuentas pendientes de aprobacion,
        porque todavia no usan el sistema: decirles que "pasamos a la 2.0" solo
        genera una consulta a soporte.
        """
        cuentas = (
            User.objects.filter(is_active=True, is_staff=False, is_superuser=False)
            .exclude(groups__name=GRUPO_IMPRENTA)
            .order_by("username")
        )
        con_correo = [u for u in cuentas if u.email]
        sin_correo = [u for u in cuentas if not u.email]
        return con_correo, sin_correo

    def _informar_del_censo(self, destinatarios, sin_correo):
        self.stdout.write(f"Sindicatos a los que escribir: {len(destinatarios)}")

        if not sin_correo:
            return

        # Se nombran de uno en uno a proposito: son los que no se van a enterar
        # por esta via y hay que llegarles por otra.
        self.stdout.write(self.style.WARNING(
            f"\n{len(sin_correo)} sindicato(s) SIN correo. No recibiran el aviso; "
            "avisales por telefono o por los canales de la organizacion:",
        ))
        for usuario in sin_correo:
            perfil = getattr(usuario, "perfilsindicato", None)
            nombre = getattr(perfil, "nombre_identificativo", "") or "(sin nombre declarado)"
            self.stdout.write(f"  - {usuario.username}  ->  {nombre}")

    # --- El envio ---

    def _comprobar_que_el_correo_saldra(self):
        """Para no descubrir a mitad de un envio masivo que no sale ninguno."""
        if settings.DEFAULT_FROM_EMAIL == REMITENTE_DE_DJANGO:
            raise CommandError(
                "DEFAULT_FROM_EMAIL es 'webmaster@localhost', el valor por defecto de "
                "Django. Los mensajes saldrian con un remitente que el destino rechaza. "
                "Configuralo en el .env antes de enviar.",
            )

    def _enviar(self, destinatarios, url):
        asunto = render_to_string(PLANTILLA_ASUNTO).strip()

        # Una sola conexion SMTP para todo el lote: abrir y cerrar una por
        # mensaje es lo que hace que un servidor de correo te corte a mitad.
        conexion = get_connection()
        conexion.open()
        enviados = 0
        try:
            for usuario in destinatarios:
                cuerpo = render_to_string(PLANTILLA_CUERPO, {
                    "usuario": usuario.get_username(),
                    "url": url,
                })
                # UN destinatario por mensaje. Ni cc ni bcc: ver la cabecera.
                EmailMessage(
                    subject=asunto,
                    body=cuerpo,
                    to=[usuario.email],
                    connection=conexion,
                ).send()
                enviados += 1
        finally:
            conexion.close()

        return enviados

    def _enseñar_una_muestra(self, destinatarios, url):
        if not destinatarios:
            return

        cuerpo = render_to_string(PLANTILLA_CUERPO, {
            "usuario": destinatarios[0].get_username(),
            "url": url,
        })
        self.stdout.write("\n--- Asi quedaria el mensaje ---")
        self.stdout.write(render_to_string(PLANTILLA_ASUNTO).strip())
        self.stdout.write(cuerpo)

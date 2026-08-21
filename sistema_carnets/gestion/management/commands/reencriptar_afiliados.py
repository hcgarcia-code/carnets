"""Reescribe los datos personales con la clave de cifrado activa.

Al rotar una clave, lo ya guardado sigue cifrado con la anterior: por eso la
clave antigua tiene que seguir configurada, y por eso no se puede destruir
—mientras quede una sola fila bajo ella, borrarla dejaría ese dato
irrecuperable—. Este comando reescribe todas las filas con la clave activa,
que es lo que permite retirar las anteriores y cerrar la rotación.

Se usa `bulk_update` a propósito: no emite señales, así que django-simple-history
no crea una entrada de historial por afiliado. Aquí eso es justo lo que se
busca, porque no está cambiando ningún dato —solo la clave con la que está
cifrado— y llenar el registro de auditoría de cambios que no ha hecho nadie
sería peor que inútil. (Ojo: en la carga de Excel el razonamiento es el
contrario y por eso allí se usa `bulk_create_with_history`; ver views.py.)
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion.crypto import TextoNoDescifrable, clave_activa_id
from gestion.models import Afiliado

CAMPOS_CIFRADOS = ["nombre_apellidos", "num_afiliado", "notas_historicas"]

# ponytail: se cargan todas las filas en memoria. Con el volumen actual (unos
# miles de afiliados y su historial) son unas pocas decenas de MB. Si la tabla
# de historial creciera mucho, hacerlo por lotes con un recorrido por rangos de
# clave primaria.
TAMANO_LOTE = 500


class Command(BaseCommand):
    help = (
        "Reescribe los datos personales cifrados usando la clave activa, para "
        "poder retirar las claves anteriores tras una rotación."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo informa de cuántas filas se reescribirían; no escribe nada.",
        )

    def handle(self, *args, **opciones):
        solo_simular = opciones["dry_run"]
        self.stdout.write(f"Clave activa: {clave_activa_id()}")

        # El historial va incluido: de nada sirve reescribir al afiliado si su
        # historial de auditoría se queda bajo la clave antigua.
        modelos = [Afiliado, Afiliado.history.model]
        total = 0

        with transaction.atomic():
            for modelo in modelos:
                nombre = modelo._meta.verbose_name_plural
                # Leer descifra con la clave que corresponda. Las filas cuya
                # clave ya no esté configurada no revientan la lectura: llegan
                # marcadas, y hay que detectarlas aquí para decir cuáles son en
                # vez de dejar que falle la escritura con un error opaco.
                registros = list(modelo.objects.all())
                total += len(registros)

                ilegibles = [
                    registro.pk
                    for registro in registros
                    if any(
                        isinstance(getattr(registro, campo), TextoNoDescifrable)
                        for campo in CAMPOS_CIFRADOS
                    )
                ]
                if ilegibles:
                    raise CommandError(
                        f"{len(ilegibles)} fila(s) de {nombre} están cifradas con una clave "
                        f"que ya no está configurada y no se pueden reescribir: "
                        f"{ilegibles[:20]}{' ...' if len(ilegibles) > 20 else ''}. "
                        "Vuelve a añadir esa clave a la configuración y repite. "
                        "No se ha modificado nada.",
                    )

                if solo_simular:
                    self.stdout.write(f"  {nombre}: {len(registros)} fila(s) se reescribirían.")
                    continue

                if registros:
                    # Al guardar se cifra con la clave activa.
                    modelo.objects.bulk_update(
                        registros, CAMPOS_CIFRADOS, batch_size=TAMANO_LOTE,
                    )
                self.stdout.write(f"  {nombre}: {len(registros)} fila(s) reescritas.")

        if solo_simular:
            self.stdout.write(
                self.style.WARNING(f"Simulación: no se ha escrito nada ({total} fila(s))."),
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{total} fila(s) reescritas con la clave activa. "
                    "Ya se pueden retirar las claves anteriores de la configuración.",
                ),
            )

"""Anonimiza los afiliados cuyo plazo de conservacion ha vencido.

RGPD Art. 5.1.e (limitacion del plazo de conservacion) y Art. 17 (supresion).
La EIPD fija tres anios desde la baja: pasado ese plazo los datos ya no son
necesarios para la finalidad que los legitimaba, y conservarlos deja de estar
amparado.

Se anonimiza en vez de borrar la fila para conservar el recuento historico de
carnets emitidos, que no identifica a nadie. Lo que desaparece es el vinculo
entre una persona y su afiliacion sindical, que es el dato de categoria
especial (Art. 9).

El historial se anonimiza tambien, y esa es la parte que de verdad importa:
`HistoricalRecords()` guarda una copia de cada version del afiliado para
siempre. Anonimizar solo la fila viva dejaria el nombre anterior intacto en
`gestion_historicalafiliado` --cifrado, pero recuperable con la clave--, es
decir, dejaria sin suprimir justo el dato que se acaba de declarar suprimido.

Pensado para cron trimestral. Antes de la primera pasada, conviene ejecutarlo
con --dry-run: lo que hace es irreversible por definicion.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from gestion.auditoria import ACCIONES, registrar
from gestion.models import Afiliado

# Valores con los que se sustituyen los datos personales. num_afiliado cumple
# el formato de seis digitos que valida el modelo, para que la fila siga siendo
# valida si alguien la abre en el admin.
NOMBRE_ANONIMO = "ANONIMIZADO"
NUM_AFILIADO_ANONIMO = "000000"

ANIOS_DE_CONSERVACION = 3


class Command(BaseCommand):
    help = "Anonimiza los afiliados de baja con el plazo de conservacion vencido (RGPD Art. 5.1.e)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--anios", type=int, default=ANIOS_DE_CONSERVACION,
            help=f"Plazo de conservacion desde la baja (por defecto {ANIOS_DE_CONSERVACION}).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Dice a cuantos afectaria sin tocar nada.",
        )

    def handle(self, *args, **opciones):
        limite = timezone.now() - timedelta(days=365 * opciones["anios"])

        vencidos = Afiliado.objects.filter(estado="BAJA", fecha_baja__lt=limite)
        identificadores = list(vencidos.values_list("pk", flat=True))

        # Bajas anteriores a que existiera fecha_baja: no se puede saber cuando
        # vencen, asi que no se tocan. Pero callarlo las dejaria invisibles para
        # siempre, que es el incumplimiento que este comando viene a cerrar.
        sin_fecha = Afiliado.objects.filter(estado="BAJA", fecha_baja__isnull=True).count()
        if sin_fecha:
            self.stdout.write(
                f"AVISO: {sin_fecha} afiliado(s) de baja sin fecha de baja. No se pueden "
                "expurgar porque no hay plazo que contar; revisalos a mano.",
            )

        if not identificadores:
            self.stdout.write("No hay ningun afiliado con el plazo vencido.")
            return

        if opciones["dry_run"]:
            self.stdout.write(
                f"[dry-run] Se anonimizarian {len(identificadores)} afiliado(s) "
                f"dados de baja antes de {limite.date()}.",
            )
            return

        with transaction.atomic():
            # El historial primero: si el proceso muere entre las dos
            # operaciones, es preferible un historial ya limpio con la fila viva
            # aun por limpiar (la siguiente pasada la coge) que al reves, que
            # dejaria el dato en el historial sin nada que vuelva a senalarlo.
            Afiliado.history.filter(id__in=identificadores).update(
                nombre_apellidos=NOMBRE_ANONIMO,
                num_afiliado=NUM_AFILIADO_ANONIMO,
                notas_historicas="",
            )
            Afiliado.objects.filter(pk__in=identificadores).update(
                nombre_apellidos=NOMBRE_ANONIMO,
                num_afiliado=NUM_AFILIADO_ANONIMO,
                notas_historicas="",
            )

        # Se anota despues de confirmar la transaccion: registrar antes dejaria
        # constancia de un expurgado que quiza no llego a ocurrir.
        registrar(
            ACCIONES.AFILIADOS_EXPURGADOS,
            usuario="expurgar_afiliados",
            cantidad=len(identificadores),
            ids=identificadores,
            anios=opciones["anios"],
        )

        self.stdout.write(
            f"Anonimizados {len(identificadores)} afiliado(s) y su historial "
            f"(baja anterior a {limite.date()}).",
        )

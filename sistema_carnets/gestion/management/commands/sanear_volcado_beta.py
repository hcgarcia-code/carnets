"""Sanea el volcado del beta para poder reimportar las filas que se rechazaron.

El volcado real trae 407 afiliados cuyo `estado` no es ALTA ni BAJA --lleva un
codigo de federacion, `"202` o `"201`-- y 344 con una `lengua` que no existe.
Son las mismas filas: un problema, no dos.

**Este comando no recupera ese dato, porque no se puede.** De `"202` no se
deduce si esa persona esta de alta o de baja: la informacion no esta en el
volcado. Lo que hace es aplicar una decision tomada fuera --por defecto, asumir
ALTA-- y dejar constancia de cuantas filas se han tocado y de que sindicatos
son.

Esa constancia es la razon de que esto sea un comando y no un `sed`: se esta
fijando por asuncion el estado de afiliacion de cientos de personas, y dentro de
un ano hara falta poder decir cuantas fueron y con que criterio. Guarda la
salida junto al volcado original.

Escribe en un archivo NUEVO y se niega a pisar uno existente. El volcado
original no se toca: es la unica prueba de lo que decia el beta de verdad.

Despues:

    manage.py importar_desde_beta beta_saneado.json --dry-run
    manage.py importar_desde_beta beta_saneado.json

`importar_desde_beta` no duplica --descarta los afiliados que ya existan para
el mismo sindicato y numero--, asi que se puede lanzar sobre el volcado saneado
entero: solo entraran las filas que faltaban.
"""

import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

MODELO_AFILIADO = "gestion.afiliado"

ESTADOS_VALIDOS = ("ALTA", "BAJA")
LENGUAS_VALIDAS = ("A", "C")


class Command(BaseCommand):
    help = "Sanea un volcado del beta: fija por asuncion el estado y la lengua ilegibles."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Volcado original (no se modifica).")
        parser.add_argument(
            "--salida", required=True,
            help="Archivo a escribir. Se niega a pisar uno que ya exista.",
        )
        parser.add_argument(
            "--estado", default="ALTA", choices=ESTADOS_VALIDOS,
            help="Valor a poner donde el estado es ilegible (por defecto ALTA).",
        )
        parser.add_argument(
            "--lengua", default="A", choices=LENGUAS_VALIDAS,
            help="Valor a poner donde la lengua es invalida (por defecto A, castellano).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Dice lo que cambiaria sin escribir nada.",
        )

    def handle(self, *args, **opciones):
        entrada = Path(opciones["archivo"])
        salida = Path(opciones["salida"])

        if not entrada.is_file():
            raise CommandError(f"No se encuentra {entrada}.")
        if salida.exists():
            raise CommandError(
                f"{salida} ya existe. Elige otro nombre: pisar un saneado anterior "
                "borraria la constancia de lo que se cambio la vez pasada.",
            )

        filas = self._leer(entrada)
        estados, lenguas, por_sindicato = self._sanear(
            filas, opciones["estado"], opciones["lengua"],
        )

        self._informar(estados, lenguas, por_sindicato, opciones["estado"], opciones["lengua"])

        if opciones["dry_run"]:
            self.stdout.write(self.style.WARNING("\nEN SECO: no se ha escrito nada."))
            return

        salida.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"\nEscrito {salida}."))
        self.stdout.write(
            "Ahora:\n"
            f"  manage.py importar_desde_beta {salida} --dry-run\n"
            f"  manage.py importar_desde_beta {salida}",
        )

    def _leer(self, entrada):
        try:
            filas = json.loads(entrada.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CommandError(f"No se pudo leer {entrada}: {error}") from error

        if not isinstance(filas, list):
            raise CommandError("El volcado no tiene la forma de un dumpdata (una lista).")

        return filas

    def _sanear(self, filas, estado_nuevo, lengua_nueva):
        estados = lenguas = 0
        por_sindicato = Counter()

        for fila in filas:
            if str(fila.get("model", "")).lower() != MODELO_AFILIADO:
                continue

            campos = fila.get("fields", {})
            tocada = False

            if str(campos.get("estado", "")).strip() not in ESTADOS_VALIDOS:
                campos["estado"] = estado_nuevo
                estados += 1
                tocada = True

            if str(campos.get("lengua", "")).strip() not in LENGUAS_VALIDAS:
                campos["lengua"] = lengua_nueva
                lenguas += 1
                tocada = True

            if tocada:
                por_sindicato[campos.get("sindicato_usuario")] += 1

        return estados, lenguas, por_sindicato

    def _informar(self, estados, lenguas, por_sindicato, estado_nuevo, lengua_nueva):
        if not estados and not lenguas:
            self.stdout.write("No hay nada que sanear: todas las filas son validas.")
            return

        self.stdout.write(self.style.WARNING(
            "Esto NO recupera el dato original: lo fija por ASUNCION. De un estado "
            "ilegible no se deduce si la persona esta de alta o de baja.",
        ))
        self.stdout.write(f"\nEstados ilegibles -> {estado_nuevo}: {estados} fila(s)")
        self.stdout.write(f"Lenguas invalidas -> {lengua_nueva}: {lenguas} fila(s)")

        self.stdout.write(f"\nSindicatos afectados: {len(por_sindicato)}")
        for identificador, cuantas in por_sindicato.most_common(20):
            self.stdout.write(f"  - sindicato {identificador}: {cuantas} fila(s)")
        if len(por_sindicato) > 20:
            self.stdout.write(f"  ... y {len(por_sindicato) - 20} sindicato(s) mas")

        self.stdout.write(
            "\nGuarda esta salida junto al volcado original: es la constancia de "
            "cuantas fichas se fijaron por asuncion y con que criterio.",
        )

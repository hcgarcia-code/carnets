"""Deja el entorno listo para una prueba de extremo a extremo.

Crea las tres cuentas que hacen falta (administrador, sindicato e imprenta),
el grupo Imprenta y un Excel de ejemplo con la plantilla oficial, para no
tener que montarlo a mano cada vez.

SOLO PARA DESARROLLO. Crea cuentas cuya contraseña se imprime por pantalla y
afiliados inventados: en un servidor real eso es a la vez una puerta de
entrada sin aprobar y una contaminación de los datos verdaderos. Por eso se
niega a ejecutarse con DEBUG=False o sobre una base de datos que ya contenga
afiliados.
"""

import secrets

import pandas as pd
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion.models import Afiliado
from gestion.views import COLUMNAS_REQUERIDAS, GRUPO_IMPRENTA

EXCEL_POR_DEFECTO = "afiliados_de_ejemplo.xlsx"

# Filas de ejemplo en el formato real de la plantilla ("01 - Territorial"): la
# vista se queda con lo anterior al guion, así que el archivo de prueba tiene
# que ejercitar ese mismo troceado y no una versión simplificada.
FILAS_DE_EJEMPLO = [
    ('01 - Territorial Madrid', '12345 - Local Centro', '02 - Metal',
     '003 - Sindicato Metal', '000101', 'Ana López García', 'A', 'ALTA'),
    ('01 - Territorial Madrid', '12345 - Local Centro', '02 - Metal',
     '003 - Sindicato Metal', '000102', 'Bruno Martín Sanz', 'A', 'ALTA'),
    ('01 - Territorial Madrid', '12345 - Local Centro', '02 - Metal',
     '003 - Sindicato Metal', '000103', 'Carmen Ruiz Ortega', 'A', 'ALTA'),
    ('08 - Territorial Barcelona', '54321 - Local Litoral', '04 - Enseñanza',
     '007 - Sindicato Enseñanza', '000201', 'Jordi Puig Ferrer', 'C', 'ALTA'),
    ('08 - Territorial Barcelona', '54321 - Local Litoral', '04 - Enseñanza',
     '007 - Sindicato Enseñanza', '000202', 'Marta Soler Vidal', 'C', 'BAJA'),
]


class Command(BaseCommand):
    help = "Prepara cuentas y datos de ejemplo para probar la aplicación (solo desarrollo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--forzar", action="store_true",
            help="Ejecuta aunque ya existan afiliados (para repetir una prueba).",
        )
        parser.add_argument(
            "--excel", default=EXCEL_POR_DEFECTO,
            help=f"Ruta del Excel de ejemplo a generar (defecto: {EXCEL_POR_DEFECTO}).",
        )

    def handle(self, *args, **opciones):
        if not settings.DEBUG:
            raise CommandError(
                "DEBUG está desactivado: esto parece un entorno de producción. "
                "Este comando crea cuentas de acceso con contraseña conocida y "
                "afiliados ficticios, y no debe ejecutarse aquí."
            )

        if not opciones["forzar"] and Afiliado.objects.exists():
            raise CommandError(
                f"La base de datos ya contiene {Afiliado.objects.count()} afiliado(s). "
                "Si de verdad es un entorno de pruebas, repite con --forzar."
            )

        with transaction.atomic():
            grupo, _ = Group.objects.get_or_create(name=GRUPO_IMPRENTA)
            credenciales = [
                self._crear_cuenta("admin", superusuario=True),
                self._crear_cuenta("sindicato"),
                self._crear_cuenta("imprenta", grupo=grupo),
            ]

        ruta_excel = self._generar_excel(opciones["excel"])
        self._instrucciones(credenciales, ruta_excel)

    def _crear_cuenta(self, nombre, *, superusuario=False, grupo=None):
        """Crea o reutiliza la cuenta y le asigna una contraseña nueva al azar.

        Reasigna la contraseña siempre, también si la cuenta ya existía: no se
        guarda en ninguna parte (solo se imprime), así que reejecutar el
        comando es la única forma de recuperar el acceso si se pierde.
        """
        # secrets, no random: aunque sea un entorno de pruebas, estas cuentas
        # acaban a veces en máquinas accesibles desde la red local.
        contrasena = secrets.token_urlsafe(12)
        usuario, _ = User.objects.get_or_create(username=nombre)
        usuario.set_password(contrasena)
        usuario.is_active = True
        # Solo el administrador entra al admin de Django. La imprenta tiene su
        # propio panel, deliberadamente ciego a los datos personales, y darle
        # is_staff lo dejaría sin efecto: vería las fichas completas.
        usuario.is_staff = superusuario
        usuario.is_superuser = superusuario
        usuario.save()
        if grupo:
            usuario.groups.add(grupo)
        return nombre, contrasena

    def _generar_excel(self, ruta):
        df = pd.DataFrame(FILAS_DE_EJEMPLO, columns=COLUMNAS_REQUERIDAS)
        df.to_excel(ruta, index=False, engine='openpyxl')
        return ruta

    def _instrucciones(self, credenciales, ruta_excel):
        escribir = self.stdout.write
        # Solo ASCII en esta salida: la consola de Windows usa cp1252 y un
        # simbolo fuera de ese juego (un tick, una flecha) aborta el comando
        # entero con UnicodeEncodeError despues de haberlo hecho ya todo.
        escribir(self.style.SUCCESS("\nEntorno de pruebas preparado.\n"))

        escribir("CUENTAS (la contraseña solo se muestra ahora; se pierde al cerrar):")
        for nombre, contrasena in credenciales:
            escribir(f"    {nombre:<12} {contrasena}")

        escribir(f"\nEXCEL DE EJEMPLO: {ruta_excel} ({len(FILAS_DE_EJEMPLO)} afiliados)")
        escribir(
            "\nARRANCA EL SERVIDOR:\n"
            "    python sistema_carnets/manage.py runserver\n"
            "\nRECORRIDO DE PRUEBA:\n"
            "  1. /alta/            alta de un sindicato nuevo (queda inactivo)\n"
            "  2. /admin/auth/user/ entra como 'admin' y aprueba ese alta\n"
            "  3. /login/           entra como 'sindicato', firma el acuerdo y sube el Excel\n"
            "  4. /admin/           como 'admin', selecciona afiliados -> accion 2 (exportar)\n"
            "  5. /panel-imprenta/  entra como 'imprenta': ve los números, nunca los nombres\n",
        )

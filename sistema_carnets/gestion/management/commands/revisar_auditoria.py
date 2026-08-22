"""Revisa el registro de auditoria y avisa por correo si hay algo reseniable.

Pensado para cron, una vez por hora:

    0 * * * * cd /ruta && python manage.py revisar_auditoria

Por que un comando periodico y no un correo desde el propio logger: un ataque
de fuerza bruta genera un aviso por intento, y justo cuando hace falta leer la
alerta el buzon esta inservible. Al agrupar por ventana, el resumen va acotado
por construccion.

Esto es el escalon de mientras tanto. El destino final del registro es un
agregador externo de solo-adicion (ver deploy/auditoria_centralizada.md), y las
alertas serias deben vivir alli: un archivo en el propio servidor lo puede
editar quien lo haya comprometido, y entonces este comando no ve nada.
"""

import json
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand

from gestion.auditoria import ACCIONES

VENTANA_POR_DEFECTO_HORAS = 1

# Cuantas veces tiene que aparecer una accion en la ventana para merecer aviso.
# Un bloqueo suelto es alguien que ha olvidado su contrasena; una racha es un
# ataque. Una exportacion, en cambio, saca datos personales a un archivo
# descargable: con una basta.
UMBRALES = {
    ACCIONES.LOGIN_BLOQUEADO: 3,
    ACCIONES.AFILIADOS_EXPORTADOS: 1,
    ACCIONES.ACCESO_DENEGADO: 3,
}


class Command(BaseCommand):
    help = "Revisa el registro de auditoria de las ultimas horas y avisa por correo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--horas", type=float, default=VENTANA_POR_DEFECTO_HORAS,
            help=f"Ventana a revisar (defecto: {VENTANA_POR_DEFECTO_HORAS}).",
        )

    def handle(self, *args, **opciones):
        # Solo ASCII en la salida: la consola de Windows usa cp1252.
        escribir = self.stdout.write

        ruta = getattr(settings, "AUDITORIA_LOG_PATH", "") or ""
        if not ruta:
            # Callarse aqui haria que un despliegue sin el registro configurado
            # pareciese vigilado sin estarlo, que es peor que no tener el aviso.
            escribir(self.style.WARNING(
                "AUDITORIA_LOG_PATH no esta configurado: no hay registro que "
                "revisar. Definelo en el .env del servidor (ver "
                "deploy/auditoria_centralizada.md).",
            ))
            return

        desde = datetime.now(timezone.utc) - timedelta(hours=opciones["horas"])
        try:
            sucesos = self._leer(ruta, desde)
        except OSError as exc:
            escribir(self.style.ERROR(f"No se pudo leer {ruta}: {exc}"))
            return

        destacados = {
            accion: apariciones
            for accion, apariciones in sucesos.items()
            if len(apariciones) >= UMBRALES.get(accion, 10**9)
        }

        if not destacados:
            escribir(f"Sin incidencias en las ultimas {opciones['horas']} hora(s).")
            return

        cuerpo = self._redactar(destacados, opciones["horas"])
        mail_admins(
            subject=f"[Carnets] {len(destacados)} tipo(s) de suceso a revisar",
            message=cuerpo,
            fail_silently=False,
        )
        escribir(self.style.WARNING(f"Aviso enviado:\n{cuerpo}"))

    def _leer(self, ruta, desde):
        sucesos = {}
        with open(ruta, encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    registro = json.loads(linea)
                    momento = datetime.fromisoformat(registro["ts"])
                except (ValueError, KeyError, TypeError):
                    # Una linea corrupta (el proceso murio a media escritura)
                    # no puede impedir ver las demas: seria la forma mas facil
                    # de ocultar un incidente real.
                    continue
                if momento >= desde:
                    sucesos.setdefault(registro.get("accion", "?"), []).append(registro)
        return sucesos

    def _redactar(self, destacados, horas):
        lineas = [f"Sucesos en las ultimas {horas} hora(s):", ""]
        for accion, apariciones in sorted(destacados.items()):
            lineas.append(f"  {accion}: {len(apariciones)} vez/veces")
            for registro in apariciones[:10]:
                detalle = " ".join(
                    f"{clave}={valor}"
                    for clave, valor in sorted(registro.items())
                    if clave not in ("accion",)
                )
                lineas.append(f"      {detalle}")
            if len(apariciones) > 10:
                lineas.append(f"      (y {len(apariciones) - 10} mas)")
            lineas.append("")
        lineas.append(
            "Este aviso no contiene datos personales: el registro de auditoria "
            "no los guarda a proposito.",
        )
        return "\n".join(lineas)

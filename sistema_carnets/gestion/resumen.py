"""Qué está pendiente de atención, para la portada del admin.

El administrador entraba a `/admin/` y se encontraba la lista de modelos de
Django. Todo lo que aquí se cuenta ya estaba en la base de datos, pero para
verlo había que recordar qué listado filtrar y con qué parámetro: las altas
esperando aprobación, los sindicatos que usan el sistema sin haber firmado el
acuerdo, los que dejaron de subir. Nada de eso avisa solo.

Reglas que gobiernan este módulo:

- **Solo recuentos.** Aquí no aparece ni un dato de afiliado. Los números
  agregados no identifican a nadie; en cuanto se enseñe un nombre, esta pantalla
  pasa a ser un punto más donde se descifra, y habría que auditarla como el
  listado de afiliados.
- **Cada aviso lleva a su listado ya filtrado.** Un número que no se puede
  pulsar obliga a saber construir el filtro, que es justo el trabajo que esto
  viene a quitar.
- **Solo se avisa de lo accionable.** Sin nada pendiente no se pinta ningún
  aviso: así una portada vacía significa «no hay nada que hacer» y no «no me he
  fijado».
"""

from datetime import datetime, timedelta, timezone as _utc

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Max, Q
from django.urls import reverse
from django.utils import timezone

from .auditoria import ACCIONES, leer_sucesos
from .models import Afiliado, PerfilSindicato

# Desde cuántos días sin cargar se considera dormido un sindicato. No es un
# fallo técnico —nada falla— pero sí el aviso de que alguien dejó de subir altas
# y sus afiliados se están quedando sin carnet.
DIAS_SIN_ACTIVIDAD = 60

# Ventana de la que se cuentan los bloqueos de acceso. La misma que revisa el
# comando `revisar_auditoria` por cron, para que las dos cifras sean comparables.
HORAS_DE_BLOQUEOS = 1

# Cuánto se lee de la cola del registro de auditoría. El archivo es de
# solo-adición y crece sin límite, y esto se ejecuta en cada carga de `/admin/`:
# sin tope, la portada se volvería más lenta cuanto más se usara el sistema.
# 2 MB son unas 10.000 líneas, muy por encima de una hora de actividad normal.
MAX_BYTES_AUDITORIA = 2 * 1024 * 1024


def _aviso(texto, url=None, nivel="aviso"):
    return {"texto": texto, "url": url, "nivel": nivel}


def _url(vista, consulta=""):
    return reverse(vista) + consulta


def _cuentas_pendientes_de_aprobar():
    # `perfil__isnull=False` deja fuera a las cuentas que no son de sindicato:
    # una cuenta de personal desactivada no es un alta esperando revisión.
    pendientes = User.objects.filter(is_active=False, perfil__isnull=False).count()
    if not pendientes:
        return None
    return _aviso(
        f"{pendientes} cuenta(s) de sindicato pendientes de aprobar",
        _url('admin:auth_user_changelist', '?is_active__exact=0'),
    )


def _sin_acuerdo_firmado():
    # Solo entre las cuentas ya aprobadas: una que todavía espera aprobación no
    # ha podido firmar nada, así que contarla sería un aviso que nadie puede
    # atender. El enlace lleva los dos filtros para que el listado enseñe
    # exactamente lo que dice el número.
    sin_firmar = PerfilSindicato.objects.filter(
        usuario__is_active=True, acuerdo_aceptado=False,
    ).count()
    if not sin_firmar:
        return None
    return _aviso(
        f"{sin_firmar} sindicato(s) aprobados que aún no han firmado el acuerdo",
        _url(
            'admin:gestion_perfilsindicato_changelist',
            '?acuerdo_aceptado__exact=0&usuario__is_active__exact=1',
        ),
    )


def _sindicatos_dormidos():
    limite = timezone.now() - timedelta(days=DIAS_SIN_ACTIVIDAD)
    dormidos = (
        PerfilSindicato.objects
        .filter(usuario__is_active=True)
        .annotate(_ultima=Max('usuario__subidas__fecha'))
        .filter(Q(_ultima__lt=limite) | Q(_ultima__isnull=True))
        .count()
    )
    if not dormidos:
        return None
    return _aviso(
        f"{dormidos} sindicato(s) sin cargar altas en {DIAS_SIN_ACTIVIDAD} días",
        _url(
            'admin:gestion_perfilsindicato_changelist',
            '?actividad=dormidos&usuario__is_active__exact=1',
        ),
    )


def _pendientes_de_imprimir():
    pendientes = Afiliado.objects.filter(
        estado_impresion=Afiliado.ESTADO_PENDIENTE,
    ).count()
    if not pendientes:
        return None
    return _aviso(
        f"{pendientes} carnet(s) pendientes de enviar a imprenta",
        _url(
            'admin:gestion_afiliado_changelist',
            f'?estado_impresion__exact={Afiliado.ESTADO_PENDIENTE}',
        ),
    )


def _bloqueos_de_acceso():
    """Bloqueos por intentos fallidos en la última hora, leídos del registro.

    No hay enlace a ningún listado: el registro de auditoría no es una tabla de
    la base de datos a propósito —sale de la máquina hacia un destino de
    solo-adición— y meterlo aquí lo dejaría a merced de la misma cuenta que
    audita. Ver la cabecera de auditoria.py.
    """
    ruta = getattr(settings, "AUDITORIA_LOG_PATH", "") or ""
    if not ruta:
        # Callarse aquí haría que un despliegue sin registro pareciese vigilado
        # sin estarlo, que es peor que no tener el aviso.
        return _aviso(
            "El registro de auditoría no está configurado: los accesos a datos "
            "personales no se están guardando (AUDITORIA_LOG_PATH en el .env)",
            nivel="alerta",
        )

    desde = datetime.now(_utc.utc) - timedelta(hours=HORAS_DE_BLOQUEOS)
    try:
        sucesos, truncado = leer_sucesos(ruta, desde, max_bytes=MAX_BYTES_AUDITORIA)
    except OSError:
        # La portada del admin es la pantalla desde la que se arregla cualquier
        # cosa: un registro ilegible no puede impedir llegar a ella.
        return _aviso(
            f"No se ha podido leer el registro de auditoría ({ruta})",
            nivel="alerta",
        )

    bloqueos = len(sucesos.get(ACCIONES.LOGIN_BLOQUEADO, []))
    if not bloqueos:
        return None
    # Con el archivo truncado la cifra es un mínimo, no un total: decir "23"
    # cuando fueron miles tranquilizaría justo durante un ataque.
    cantidad = f"Más de {bloqueos}" if truncado else str(bloqueos)
    return _aviso(
        f"{cantidad} bloqueo(s) por intentos fallidos de acceso en la última hora",
        nivel="alerta",
    )


def resumen_operativo():
    """Lista de avisos para la portada del admin. Vacía si no hay nada que hacer."""
    candidatos = (
        _bloqueos_de_acceso(),
        _cuentas_pendientes_de_aprobar(),
        _sin_acuerdo_firmado(),
        _pendientes_de_imprimir(),
        _sindicatos_dormidos(),
    )
    return [aviso for aviso in candidatos if aviso is not None]

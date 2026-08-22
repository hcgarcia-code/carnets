"""Alguien tiene que mirar el registro de auditoría, o no sirve de nada.

El registro es correcto (JSON por línea, sin datos personales, preparado para
un destino de solo-adición), pero hasta ahora nadie lo leía: un ataque de
fuerza bruta o una exportación masiva de afiliados quedaba anotada y ahí se
quedaba, hasta que a alguien se le ocurriera abrir el archivo. Un registro que
nadie revisa documenta el incidente, no lo detecta.

Este comando se ejecuta desde cron y avisa por correo. La alternativa
—mandar un correo desde el propio logger, en el momento— tiene el problema de
que un ataque de fuerza bruta genera un correo por intento: justo cuando hace
falta leer el aviso, el buzón está inservible. Al ejecutarse cada hora, el
resumen va agrupado y acotado por construcción.

El destino final del registro es un agregador externo (ver
deploy/auditoria_centralizada.md), y ahí es donde deben vivir las alertas
serias. Esto es el escalón de mientras tanto.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from django.core import mail
from django.core.management import call_command
from io import StringIO

from gestion.auditoria import ACCIONES


def _linea(accion, hace_minutos=1, **extra):
    momento = datetime.now(timezone.utc) - timedelta(minutes=hace_minutos)
    return json.dumps({"ts": momento.isoformat(), "accion": accion, "usuario": "x", **extra})


@pytest.fixture
def registro(tmp_path, settings):
    ruta = tmp_path / "auditoria.jsonl"
    ruta.write_text("", encoding="utf-8")
    settings.AUDITORIA_LOG_PATH = str(ruta)
    settings.ADMINS = [("Responsable", "responsable@ejemplo.es")]
    return ruta


def _escribir(registro, lineas):
    registro.write_text("\n".join(lineas) + "\n", encoding="utf-8")


@pytest.mark.django_db
def test_avisa_de_una_racha_de_bloqueos_de_login(registro):
    """Varios bloqueos seguidos es la firma de un ataque en curso."""
    _escribir(registro, [_linea(ACCIONES.LOGIN_BLOQUEADO) for _ in range(4)])

    call_command("revisar_auditoria", stdout=StringIO())

    assert len(mail.outbox) == 1
    assert ACCIONES.LOGIN_BLOQUEADO in mail.outbox[0].body


@pytest.mark.django_db
def test_avisa_de_una_exportacion_de_afiliados(registro):
    """Sacar datos personales a un archivo descargable es la operación más
    sensible: una sola ya merece aviso."""
    _escribir(registro, [_linea(ACCIONES.AFILIADOS_EXPORTADOS, cantidad=1500)])

    call_command("revisar_auditoria", stdout=StringIO())

    assert len(mail.outbox) == 1
    assert "1500" in mail.outbox[0].body


@pytest.mark.django_db
def test_no_avisa_cuando_no_hay_nada_reseniable(registro):
    """Un correo por hora sin contenido enseña a ignorar los correos."""
    _escribir(registro, [_linea(ACCIONES.LOGIN_CORRECTO), _linea(ACCIONES.AFILIADOS_CARGADOS)])

    call_command("revisar_auditoria", stdout=StringIO())

    assert mail.outbox == []


@pytest.mark.django_db
def test_ignora_lo_anterior_a_la_ventana(registro):
    """Sin esto, cada ejecución reenviaría el mismo incidente para siempre."""
    _escribir(registro, [_linea(ACCIONES.AFILIADOS_EXPORTADOS, hace_minutos=60 * 40)])

    call_command("revisar_auditoria", "--horas", "1", stdout=StringIO())

    assert mail.outbox == []


@pytest.mark.django_db
def test_una_linea_corrupta_no_impide_revisar_el_resto(registro):
    """El archivo puede quedar cortado a media línea si el proceso muere
    escribiendo. Que eso oculte un incidente real sería lo peor posible."""
    _escribir(registro, [
        "{esto no es json valido",
        _linea(ACCIONES.AFILIADOS_EXPORTADOS, cantidad=9),
    ])

    call_command("revisar_auditoria", stdout=StringIO())

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_sin_archivo_configurado_lo_dice_en_vez_de_callar(registro, settings):
    """Si no avisara, un despliegue sin AUDITORIA_LOG_PATH pareceria estar
    vigilado cuando no lo esta."""
    settings.AUDITORIA_LOG_PATH = ""
    salida = StringIO()

    call_command("revisar_auditoria", stdout=salida)

    assert "AUDITORIA_LOG_PATH" in salida.getvalue()


def test_la_ruta_del_registro_es_un_setting_de_verdad():
    """AUDITORIA_LOG_PATH tiene que existir como setting, no solo como
    variable local de settings.py.

    Estuvo guardada en `_auditoria_log`: con guion bajo Django no la exporta,
    asi que `getattr(settings, 'AUDITORIA_LOG_PATH')` devolvia cadena vacia y
    el comando informaba de "no hay registro configurado" incluso en un
    servidor que lo tenia perfectamente configurado. Las demas pruebas no lo
    detectan porque asignan el setting directamente.
    """
    import os

    from django.conf import settings

    esperado = os.environ.get("AUDITORIA_LOG_PATH", "")
    assert hasattr(settings, "AUDITORIA_LOG_PATH")
    assert settings.AUDITORIA_LOG_PATH == esperado


@pytest.mark.django_db
def test_la_salida_es_solo_ascii(registro):
    """Consola de Windows en cp1252: mismo motivo que en los demas comandos."""
    _escribir(registro, [_linea(ACCIONES.LOGIN_BLOQUEADO) for _ in range(4)])
    salida = StringIO()

    call_command("revisar_auditoria", stdout=salida)

    salida.getvalue().encode("cp1252")

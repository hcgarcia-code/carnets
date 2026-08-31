"""TDD: la exportación a imprenta no debe volver a tocar lo ya impreso.

En el admin, seleccionar afiliados across varias páginas ("Select all N")
selecciona TODOS los que cumplan el filtro/búsqueda actual, impresos o no: si
el administrador no ha filtrado antes por "Estado de impresión: Pendiente",
"seleccionar todos" incluye también los ya enviados a imprenta. Repetir el
export sobre esos reescribe `fecha_envio_imprenta`, genera una notificación
falsa de reenvío al sindicato y deja un segundo evento de auditoría sobre el
mismo lote.

La acción debe defenderse sola: filtrar la selección a los pendientes antes de
procesar nada, sin depender de que el admin haya aplicado el filtro correcto.
"""

import json
import logging

import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from gestion.admin import AfiliadoAdmin, exportar_imprenta
from gestion.auditoria import ACCIONES
from gestion.models import Afiliado, Notificacion

pytestmark = pytest.mark.django_db


@pytest.fixture
def auditoria(caplog):
    """Captura los registros de auditoría emitidos durante el test."""
    caplog.set_level(logging.INFO, logger="auditoria")

    def leer():
        return [
            json.loads(r.getMessage())
            for r in caplog.records
            if r.name == "auditoria"
        ]

    return leer


def _crear_usuario(username="sindicato_imprenta"):
    return User.objects.create_user(username=username, password="clave-segura-123")  # noqa: S106


def _crear_afiliado(usuario, **overrides):
    datos = {
        "sindicato_usuario": usuario,
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": "123456",
        "nombre_apellidos": "Nombre Apellido",
        "lengua": "A",
        "estado": "ALTA",
    }
    datos.update(overrides)
    afiliado = Afiliado(**datos)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


def _peticion_con_mensajes(usuario):
    """RequestFactory no pasa por MessageMiddleware: sin esto, cualquier
    llamada de la acción a `modeladmin.message_user` lanzaría MessageFailure
    en vez de guardar el aviso."""
    peticion = RequestFactory().get("/admin/")
    peticion.user = usuario
    peticion.session = {}
    peticion._messages = FallbackStorage(peticion)  # noqa: SLF001 - idiom estándar de Django para probar message_user
    return peticion


def _admin():
    return AfiliadoAdmin(Afiliado, AdminSite())


def test_exportar_imprenta_no_reprocesa_lo_ya_impreso():
    usuario = _crear_usuario()
    pendiente = _crear_afiliado(usuario, num_afiliado="111111")
    ya_impreso = _crear_afiliado(usuario, num_afiliado="222222")
    ya_impreso.estado_impresion = Afiliado.ESTADO_IMPRESO
    ya_impreso.save()
    fecha_original = ya_impreso.fecha_envio_imprenta

    peticion = _peticion_con_mensajes(usuario)
    # Simula "Select all N": la vista pasa a la acción TODO lo que cumple el
    # filtro actual, sin que el admin haya restringido a "Pendiente".
    exportar_imprenta(_admin(), peticion, Afiliado.objects.all())

    ya_impreso.refresh_from_db()
    pendiente.refresh_from_db()
    assert ya_impreso.fecha_envio_imprenta == fecha_original, (
        "un afiliado ya impreso no debe reprocesarse por venir incluido en la selección"
    )
    assert pendiente.estado_impresion == Afiliado.ESTADO_IMPRESO


def test_exportar_imprenta_no_duplica_notificacion_de_lo_ya_impreso():
    usuario = _crear_usuario()
    _crear_afiliado(usuario, num_afiliado="111111")
    ya_impreso = _crear_afiliado(usuario, num_afiliado="222222")
    ya_impreso.estado_impresion = Afiliado.ESTADO_IMPRESO
    ya_impreso.save()

    peticion = _peticion_con_mensajes(usuario)
    exportar_imprenta(_admin(), peticion, Afiliado.objects.all())

    # Una sola notificación, y que hable de 1 afiliado (el pendiente), no de 2.
    assert Notificacion.objects.filter(usuario=usuario).count() == 1
    assert "de 1 afiliado" in Notificacion.objects.get(usuario=usuario).mensaje


def test_exportar_imprenta_registra_solo_los_pendientes(auditoria):
    usuario = _crear_usuario()
    _crear_afiliado(usuario, num_afiliado="111111")
    ya_impreso = _crear_afiliado(usuario, num_afiliado="222222")
    ya_impreso.estado_impresion = Afiliado.ESTADO_IMPRESO
    ya_impreso.save()

    peticion = _peticion_con_mensajes(usuario)
    exportar_imprenta(_admin(), peticion, Afiliado.objects.all())

    exportaciones = [r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_EXPORTADOS]
    assert len(exportaciones) == 1
    assert exportaciones[0]["cantidad"] == 1


def test_exportar_imprenta_avisa_de_cuantos_se_omiten():
    usuario = _crear_usuario()
    _crear_afiliado(usuario, num_afiliado="111111")
    ya_impreso = _crear_afiliado(usuario, num_afiliado="222222")
    ya_impreso.estado_impresion = Afiliado.ESTADO_IMPRESO
    ya_impreso.save()

    peticion = _peticion_con_mensajes(usuario)
    exportar_imprenta(_admin(), peticion, Afiliado.objects.all())

    textos = [str(m) for m in peticion._messages]
    assert any("1" in t and "impreso" in t.lower() for t in textos), textos


def test_exportar_imprenta_con_todo_ya_impreso_no_genera_excel_ni_reprocesa(auditoria):
    usuario = _crear_usuario()
    afiliado = _crear_afiliado(usuario)
    afiliado.estado_impresion = Afiliado.ESTADO_IMPRESO
    afiliado.save()
    fecha_original = afiliado.fecha_envio_imprenta

    peticion = _peticion_con_mensajes(usuario)
    respuesta = exportar_imprenta(_admin(), peticion, Afiliado.objects.all())

    assert respuesta is None
    afiliado.refresh_from_db()
    assert afiliado.fecha_envio_imprenta == fecha_original
    assert Notificacion.objects.count() == 0
    assert not [r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_EXPORTADOS]

    mensajes = [m.level for m in peticion._messages]
    assert messages.WARNING in mensajes

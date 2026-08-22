"""TDD: registro de auditoría de accesos a datos personales (RGPD Art. 30).

django-simple-history registra los CAMBIOS, pero no las LECTURAS: hasta ahora
nadie sabía quién había consultado o exportado los datos de los afiliados. Para
datos de categoría especial eso es justo lo que hay que poder demostrar.

Hay dos requisitos que tiran en direcciones opuestas y que estos tests fijan:

  1. Tiene que quedar constancia de quién accedió, a cuántos registros y cuándo.
  2. El propio registro NO puede contener los datos personales. Si no, se
     convierte en una segunda copia sin cifrar de lo que acabamos de cifrar,
     tirando por tierra el trabajo anterior y ampliando la superficie expuesta.
"""

import json
import logging

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory

from gestion.admin import AfiliadoAdmin, exportar_imprenta
from gestion.auditoria import ACCIONES, registrar
from gestion.models import Afiliado

pytestmark = pytest.mark.django_db

NOMBRE_REAL = "Aurora Beltrán Casanova"
NUM_AFILIADO_REAL = "556677"


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    import base64
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{base64.b64encode(bytes(range(32))).decode()}"


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


def _crear_usuario(username="sindicato_audit", **extra):
    return User.objects.create_user(username=username, password="clave-segura-123", **extra)  # noqa: S106


def _crear_afiliado(usuario, **overrides):
    datos = {
        "sindicato_usuario": usuario,
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": NUM_AFILIADO_REAL,
        "nombre_apellidos": NOMBRE_REAL,
        "lengua": "A",
        "estado": "ALTA",
    }
    datos.update(overrides)
    afiliado = Afiliado(**datos)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


# --- Forma del registro ---

def test_el_registro_es_json_con_los_campos_imprescindibles(auditoria):
    peticion = RequestFactory().get("/")
    peticion.META["REMOTE_ADDR"] = "203.0.113.7"
    registrar(ACCIONES.AFILIADOS_EXPORTADOS, peticion=peticion, usuario="ana", cantidad=3)

    registro = auditoria()[0]
    assert registro["accion"] == ACCIONES.AFILIADOS_EXPORTADOS
    assert registro["usuario"] == "ana"
    assert registro["ip"] == "203.0.113.7"
    assert registro["cantidad"] == 3
    assert registro["ts"]  # marca de tiempo


def test_se_usa_la_ip_real_de_conexion_y_no_una_cabecera_falsificable(auditoria):
    # X-Forwarded-For la pone el cliente: si se registrase esa, cualquiera
    # podría falsear su rastro en el log de auditoría.
    peticion = RequestFactory().get("/")
    peticion.META["REMOTE_ADDR"] = "203.0.113.7"
    peticion.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4"
    registrar(ACCIONES.AFILIADOS_CONSULTADOS, peticion=peticion, usuario="ana", cantidad=1)

    assert auditoria()[0]["ip"] == "203.0.113.7"


# --- El registro NO debe filtrar datos personales ---

def test_exportar_no_escribe_datos_personales_en_el_registro(auditoria):
    usuario = _crear_usuario()
    _crear_afiliado(usuario)

    peticion = RequestFactory().get("/admin/")
    peticion.user = usuario
    admin_obj = AfiliadoAdmin(Afiliado, AdminSite())
    exportar_imprenta(admin_obj, peticion, Afiliado.objects.all())

    texto = json.dumps(auditoria())
    assert NOMBRE_REAL not in texto
    assert "Beltrán" not in texto
    assert NUM_AFILIADO_REAL not in texto


# --- Los accesos que hay que poder demostrar ---

def test_exportar_a_imprenta_queda_registrado(auditoria):
    usuario = _crear_usuario()
    _crear_afiliado(usuario)
    _crear_afiliado(usuario, num_afiliado="998877")

    peticion = RequestFactory().get("/admin/")
    peticion.user = usuario
    admin_obj = AfiliadoAdmin(Afiliado, AdminSite())
    exportar_imprenta(admin_obj, peticion, Afiliado.objects.all())

    exportaciones = [r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_EXPORTADOS]
    assert len(exportaciones) == 1
    assert exportaciones[0]["cantidad"] == 2
    assert exportaciones[0]["usuario"] == usuario.username


def test_consultar_la_lista_de_afiliados_en_el_admin_queda_registrado(
    client, auditoria, entrar_en_el_admin,
):
    admin = _crear_usuario("jefa", is_staff=True, is_superuser=True)
    _crear_afiliado(admin)
    entrar_en_el_admin(client, admin)

    client.get("/admin/gestion/afiliado/")

    consultas = [r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_CONSULTADOS]
    assert consultas, "consultar la lista de afiliados debe dejar rastro"
    assert consultas[0]["usuario"] == "jefa"


def test_subir_un_excel_queda_registrado(client, auditoria):
    import io

    import pandas as pd
    from django.core.files.uploadedfile import SimpleUploadedFile

    from gestion.models import PerfilSindicato

    usuario = _crear_usuario()
    PerfilSindicato.objects.update_or_create(usuario=usuario, defaults={"acuerdo_aceptado": True})
    client.force_login(usuario)

    # Formato real de la plantilla oficial ("01 - Descripción"): así los
    # códigos llegan como texto y no los convierte pandas a número.
    fila = {
        "Confederacion": "01 - Territorial",
        "Fed_Local": "12345 - Local",
        "Fed_Sectorial": "02 - Sectorial",
        "Sindicato": "003 - Sindicato",
        "Num_Afiliado": "123456",
        "Nombre_Apellidos": NOMBRE_REAL,
        "Lengua": "A",
        "Estado": "ALTA",
    }
    buffer = io.BytesIO()
    pd.DataFrame([fila]).to_excel(buffer, index=False, engine="openpyxl")
    archivo = SimpleUploadedFile(
        "altas.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    client.post("/subir-datos/", {"archivo_excel": archivo})

    subidas = [r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_CARGADOS]
    assert subidas, "una carga de afiliados debe dejar rastro"
    assert subidas[0]["cantidad"] == 1
    texto = json.dumps(subidas)
    assert NOMBRE_REAL not in texto


# --- Autenticación ---

def test_el_login_correcto_queda_registrado(client, auditoria):
    _crear_usuario("entra")
    client.post("/login/", {"username": "entra", "password": "clave-segura-123"})

    accesos = [r for r in auditoria() if r["accion"] == ACCIONES.LOGIN_CORRECTO]
    assert accesos and accesos[0]["usuario"] == "entra"


def test_el_login_fallido_queda_registrado(client, auditoria):
    _crear_usuario("entra")
    client.post("/login/", {"username": "entra", "password": "no-es-esta"})

    fallos = [r for r in auditoria() if r["accion"] == ACCIONES.LOGIN_FALLIDO]
    assert fallos and fallos[0]["usuario"] == "entra"


def test_el_registro_de_login_fallido_no_contiene_la_contrasena(client, auditoria):
    # Una contraseña equivocada suele ser la de otra cuenta, o la correcta con
    # una errata: nunca debe acabar escrita en un log.
    _crear_usuario("entra")
    client.post("/login/", {"username": "entra", "password": "Sup3rSecreta-2026"})

    assert "Sup3rSecreta-2026" not in json.dumps(auditoria())


def test_el_bloqueo_por_fuerza_bruta_queda_registrado(client, auditoria):
    from django.core.cache import cache
    cache.clear()
    _crear_usuario("entra")

    for _ in range(6):
        client.post("/login/", {"username": "entra", "password": "no-es-esta"})

    bloqueos = [r for r in auditoria() if r["accion"] == ACCIONES.LOGIN_BLOQUEADO]
    assert bloqueos, "el bloqueo por fuerza bruta debe quedar registrado"

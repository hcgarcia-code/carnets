"""Regresiones de los fallos encontrados en la revisión del cifrado y la auditoría.

Un test por hallazgo. Cada uno falla con el código anterior a la corrección.
"""

import base64
import json
import logging

import pytest
from django.contrib.admin.models import LogEntry
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.db import connection
from django.test import RequestFactory

from gestion.admin import AfiliadoAdmin, exportar_imprenta
from gestion.auditoria import ACCIONES
from gestion.models import Afiliado

pytestmark = pytest.mark.django_db

NOMBRE_REAL = "Aurora Beltrán Casanova"
NUM_AFILIADO_REAL = "556677"

_CLAVE_A = base64.b64encode(bytes(range(32))).decode()
_CLAVE_B = base64.b64encode(bytes(range(32, 64))).decode()


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{_CLAVE_A}"


@pytest.fixture
def auditoria(caplog):
    caplog.set_level(logging.INFO, logger="auditoria")

    def leer():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "auditoria"]

    return leer


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


# --- 1. __str__ filtraba nombre y nº de afiliado a django_admin_log ---

def test_el_texto_del_afiliado_no_revela_datos_personales():
    jefa = User.objects.create_superuser("jefa", "j@x.es", "clave-larga-123")
    afiliado = _crear_afiliado(jefa)

    texto = str(afiliado)
    assert NOMBRE_REAL not in texto
    assert NUM_AFILIADO_REAL not in texto


def test_el_log_del_admin_no_guarda_datos_personales_en_claro(client, entrar_en_el_admin):
    jefa = User.objects.create_superuser("jefa", "j@x.es", "clave-larga-123")
    afiliado = _crear_afiliado(jefa)
    entrar_en_el_admin(client, jefa)

    client.post(f"/admin/gestion/afiliado/{afiliado.pk}/change/", {
        "sindicato_usuario": jefa.pk, "confederacion_territorial": "01",
        "federacion_local": "12345", "federacion_sectorial": "02",
        "sindicato_codigo": "003", "num_afiliado": NUM_AFILIADO_REAL,
        "nombre_apellidos": NOMBRE_REAL, "lengua": "A", "estado": "ALTA",
    })

    assert LogEntry.objects.exists(), "el admin deberia haber registrado el cambio"
    with connection.cursor() as cur:
        cur.execute("SELECT object_repr FROM django_admin_log")
        escrito = " ".join(str(f[0]) for f in cur.fetchall())
    assert NOMBRE_REAL not in escrito
    assert NUM_AFILIADO_REAL not in escrito


# --- 2. El usuario del POST se registraba sin acotar ---

def test_un_usuario_gigante_no_desborda_el_registro_de_auditoria(client, auditoria):
    User.objects.create_user("real", password="clave-larga-123")  # noqa: S106
    basura = "A" * 100_000

    client.post("/login/", {"username": basura, "password": "x"})

    registros = auditoria()
    assert registros, "el intento fallido debe registrarse"
    assert all(len(json.dumps(r)) < 2_000 for r in registros), (
        "un solo intento no puede escribir un registro enorme"
    )


# --- 3. Sin claves, la aplicación debe negarse a arrancar ---

def test_sin_claves_la_comprobacion_de_arranque_falla(settings):
    from django.core.exceptions import ImproperlyConfigured

    from gestion.apps import comprobar_claves_de_cifrado

    settings.CARNETS_ENCRYPTION_KEYS = ""
    with pytest.raises(ImproperlyConfigured):
        comprobar_claves_de_cifrado()


def test_con_claves_la_comprobacion_de_arranque_pasa():
    from gestion.apps import comprobar_claves_de_cifrado

    comprobar_claves_de_cifrado()  # no debe lanzar


# --- 4. Se auditaba el acceso antes de comprobar permisos ---

def test_un_acceso_denegado_no_se_registra_como_consulta(client, auditoria, entrar_en_el_admin):
    # Usuario de staff SIN permiso sobre Afiliado: entra al admin pero se le
    # deniega la vista. No puede quedar anotado igual que quien sí la vio.
    miron = User.objects.create_user(
        "miron", password="clave-larga-123", is_staff=True,  # noqa: S106
    )
    _crear_afiliado(miron)
    entrar_en_el_admin(client, miron)

    client.get("/admin/gestion/afiliado/")

    consultas = [r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_CONSULTADOS]
    assert not consultas, "un acceso denegado no es una consulta de datos"
    denegados = [r for r in auditoria() if r["accion"] == ACCIONES.ACCESO_DENEGADO]
    assert denegados, "pero sí debe quedar constancia del intento"


# --- 5. Una fila indescifrable tumbaba todo el admin ---

def test_una_fila_indescifrable_no_tumba_el_listado(settings):
    usuario = User.objects.create_user("s", password="clave-larga-123")  # noqa: S106
    _crear_afiliado(usuario)
    legible = _crear_afiliado(usuario, num_afiliado="111111")

    # Se rota la clave y se retira la anterior sin reencriptar: el primer
    # afiliado queda ilegible. El listado debe seguir funcionando.
    settings.CARNETS_ENCRYPTION_KEYS = f"nueva:{_CLAVE_B}"
    legible.nombre_apellidos = "Persona Legible"
    legible.save()

    todos = list(Afiliado.objects.all())
    assert len(todos) == 2, "el listado no puede reventar por una fila ilegible"

    por_pk = {a.pk: a for a in todos}
    assert por_pk[legible.pk].nombre_apellidos == "Persona Legible"
    ilegible = next(a for a in todos if a.pk != legible.pk)
    assert NOMBRE_REAL not in (ilegible.nombre_apellidos or "")


def test_guardar_una_fila_indescifrable_falla_en_vez_de_destruirla(settings):
    from gestion.crypto import ErrorDeDescifrado

    usuario = User.objects.create_user("s", password="clave-larga-123")  # noqa: S106
    afiliado = _crear_afiliado(usuario)

    settings.CARNETS_ENCRYPTION_KEYS = f"nueva:{_CLAVE_B}"
    recuperado = Afiliado.objects.get(pk=afiliado.pk)

    # Volver a guardar escribiría el marcador encima del dato real y lo
    # destruiría para siempre: tiene que fallar.
    with pytest.raises(ErrorDeDescifrado):
        recuperado.save()


# --- 6. El nombre del archivo subido podía llevar datos personales ---

def test_el_nombre_del_archivo_no_llega_al_registro(client, auditoria):
    import io

    import pandas as pd
    from django.core.files.uploadedfile import SimpleUploadedFile

    from gestion.models import PerfilSindicato

    usuario = User.objects.create_user("s", password="clave-larga-123")  # noqa: S106
    PerfilSindicato.objects.update_or_create(usuario=usuario, defaults={"acuerdo_aceptado": True})
    client.force_login(usuario)

    fila = {
        "Confederacion": "01 - T", "Fed_Local": "12345 - L", "Fed_Sectorial": "02 - S",
        "Sindicato": "003 - S", "Num_Afiliado": "123456",
        "Nombre_Apellidos": NOMBRE_REAL, "Lengua": "A", "Estado": "ALTA",
    }
    buffer = io.BytesIO()
    pd.DataFrame([fila]).to_excel(buffer, index=False, engine="openpyxl")
    archivo = SimpleUploadedFile(
        "altas_aurora_beltran_casanova.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    client.post("/subir-datos/", {"archivo_excel": archivo})

    texto = json.dumps(auditoria())
    assert "aurora" not in texto.lower()
    assert "beltran" not in texto.lower()


# --- 7. ids salía como texto en unas acciones y como entero en otras ---

def test_los_identificadores_se_registran_siempre_igual(client, auditoria, entrar_en_el_admin):
    jefa = User.objects.create_superuser("jefa", "j@x.es", "clave-larga-123")
    afiliado = _crear_afiliado(jefa)
    entrar_en_el_admin(client, jefa)

    client.get(f"/admin/gestion/afiliado/{afiliado.pk}/change/")

    peticion = RequestFactory().get("/admin/")
    peticion.user = jefa
    exportar_imprenta(AfiliadoAdmin(Afiliado, AdminSite()), peticion, Afiliado.objects.all())

    apertura = next(r for r in auditoria() if r["accion"] == ACCIONES.AFILIADO_ABIERTO)
    exportacion = next(r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_EXPORTADOS)

    assert apertura["ids"] == exportacion["ids"], (
        "el mismo afiliado debe aparecer igual en ambas acciones"
    )

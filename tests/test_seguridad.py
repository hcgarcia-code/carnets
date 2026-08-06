"""Tests de seguridad: configuración, validación de inputs y ausencia de SQL crudo."""

import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from gestion.models import Afiliado
from gestion.views import archivo_excel_valido

REPO_ROOT = Path(__file__).resolve().parent.parent
GESTION_DIR = REPO_ROOT / "sistema_carnets" / "gestion"


# --- Configuración sensible cargada desde el entorno (.env) ---

def test_secret_key_no_esta_vacia():
    assert settings.SECRET_KEY
    assert len(settings.SECRET_KEY) >= 20


def test_secret_key_no_es_un_valor_por_defecto_inseguro():
    valores_inseguros = {"", "changeme", "secret", "django-insecure"}
    assert settings.SECRET_KEY.lower() not in valores_inseguros


def test_debug_es_booleano():
    assert isinstance(settings.DEBUG, bool)


def test_allowed_hosts_no_esta_vacio():
    assert settings.ALLOWED_HOSTS


# --- Validación de archivos subidos (extensión y tamaño) ---

def test_rechaza_archivo_sin_extension_xlsx():
    valido, mensaje = archivo_excel_valido("afiliados.csv", 1024)
    assert valido is False
    assert "xlsx" in mensaje.lower()


def test_rechaza_archivo_ejecutable_disfrazado():
    valido, _ = archivo_excel_valido("plantilla.xlsx.exe", 1024)
    assert valido is False


def test_rechaza_archivo_demasiado_grande():
    seis_mb = 6 * 1024 * 1024
    valido, mensaje = archivo_excel_valido("afiliados.xlsx", seis_mb)
    assert valido is False
    assert "tamaño" in mensaje.lower()


def test_acepta_archivo_xlsx_valido():
    valido, mensaje = archivo_excel_valido("afiliados.xlsx", 1024)
    assert valido is True
    assert mensaje == ""


# --- Validación estricta de los datos del afiliado (RegexValidator vía full_clean) ---

def _afiliado_valido(**overrides):
    datos = {
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
    return Afiliado(**datos)


def test_afiliado_con_datos_correctos_pasa_la_validacion():
    afiliado = _afiliado_valido()
    afiliado.full_clean(exclude=["sindicato_usuario"])  # no lanza ValidationError


def test_afiliado_rechaza_codigo_no_numerico():
    afiliado = _afiliado_valido(confederacion_territorial="XX")
    try:
        afiliado.full_clean(exclude=["sindicato_usuario"])
        raise AssertionError("Se esperaba ValidationError para un código no numérico")
    except ValidationError as e:
        assert "confederacion_territorial" in e.message_dict


def test_afiliado_rechaza_intento_de_inyeccion_en_nombre():
    # El ORM parametriza los valores, pero además el campo debe aceptar el texto
    # tal cual sin ejecutarlo ni romper la validación: se guarda como texto plano.
    payload = "Robert'); DROP TABLE gestion_afiliado;--"
    afiliado = _afiliado_valido(nombre_apellidos=payload)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    assert afiliado.nombre_apellidos == payload


def test_afiliado_rechaza_longitud_incorrecta_de_num_afiliado():
    afiliado = _afiliado_valido(num_afiliado="12")
    try:
        afiliado.full_clean(exclude=["sindicato_usuario"])
        raise AssertionError("Se esperaba ValidationError por longitud incorrecta")
    except ValidationError as e:
        assert "num_afiliado" in e.message_dict


# --- Ausencia de SQL crudo y de construcción de rutas a partir de input externo ---

def test_no_hay_sql_crudo_en_el_codigo_de_la_app():
    patrones_prohibidos = re.compile(r"\.raw\(|cursor\.execute\(|connection\.cursor\(")
    for archivo in GESTION_DIR.rglob("*.py"):
        if "migrations" in archivo.parts:
            continue
        contenido = archivo.read_text(encoding="utf-8")
        assert not patrones_prohibidos.search(contenido), f"SQL crudo encontrado en {archivo}"


def test_no_se_construyen_rutas_de_archivo_con_input_del_usuario():
    patrones_prohibidos = re.compile(r"open\(|os\.path\.join\(.*request")
    for archivo in GESTION_DIR.rglob("*.py"):
        if "migrations" in archivo.parts:
            continue
        contenido = archivo.read_text(encoding="utf-8")
        assert not patrones_prohibidos.search(contenido), (
            f"Posible construcción insegura de rutas en {archivo}"
        )

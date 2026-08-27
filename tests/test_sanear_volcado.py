"""Saneado del volcado del beta antes de reimportarlo.

El volcado real trae 407 afiliados cuyo `estado` no es ALTA ni BAJA --lleva un
codigo de federacion, `"202` o `"201`-- y 344 con una `lengua` que no existe.
Son las mismas filas: un problema, no dos. El importador las rechaza, y hace
bien: el dato correcto no esta en el volcado y nadie puede deducirlo.

Este comando NO recupera ese dato, porque no se puede. Lo que hace es aplicar
una decision tomada fuera --"se asume ALTA"-- dejando constancia de cuantas
filas se han tocado y de que sindicatos son. Esa constancia es el motivo de que
esto sea un comando y no un `sed`: se esta fijando por asuncion el estado de
afiliacion de cientos de personas, y dentro de un ano hara falta poder decir
cuantas fueron y con que criterio.

Escribe en un archivo NUEVO. El volcado original no se toca: es la unica prueba
de lo que decia el beta de verdad.
"""

import json

import pytest
from django.core.management import CommandError, call_command


def _volcado(*afiliados):
    filas = [{
        "model": "auth.user", "pk": 1,
        "fields": {"username": "sov_uno", "password": "hash", "is_active": True},
    }]
    for i, (estado, lengua) in enumerate(afiliados, start=1):
        filas.append({
            "model": "gestion.afiliado", "pk": i,
            "fields": {
                "sindicato_usuario": 1, "num_afiliado": f"{i:06d}",
                "nombre_apellidos": f"Persona {i}", "estado": estado, "lengua": lengua,
                "confederacion_territorial": "01", "federacion_local": "01080",
                "federacion_sectorial": "00", "sindicato_codigo": "001",
            },
        })
    return filas


@pytest.fixture
def volcado(tmp_path):
    def _escribir(*afiliados):
        ruta = tmp_path / "beta.json"
        ruta.write_text(json.dumps(_volcado(*afiliados)), encoding="utf-8")
        return ruta
    return _escribir


def _leer(ruta):
    return [f for f in json.loads(ruta.read_text(encoding="utf-8"))
            if f["model"] == "gestion.afiliado"]


# --- Lo que arregla ---

def test_pone_alta_donde_el_estado_es_ilegible(volcado, tmp_path):
    entrada = volcado(('"202', "A"), ("ALTA", "A"), ('"201', "C"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    estados = [f["fields"]["estado"] for f in _leer(salida)]
    assert estados == ["ALTA", "ALTA", "ALTA"]


def test_respeta_las_bajas_que_si_estaban_bien(volcado, tmp_path):
    """Lo unico que no puede hacer es convertir en alta a quien SI consta de
    baja: ese dato no esta corrupto, esta dicho."""
    entrada = volcado(("BAJA", "A"), ('"202', "A"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    estados = [f["fields"]["estado"] for f in _leer(salida)]
    assert estados == ["BAJA", "ALTA"]


def test_arregla_tambien_la_lengua(volcado, tmp_path):
    """Sin esto la fila sigue sin pasar la validacion y el saneado no sirve de
    nada: son las mismas filas."""
    entrada = volcado(('"202', "Q"), ("ALTA", "Z"), ("ALTA", "C"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    lenguas = [f["fields"]["lengua"] for f in _leer(salida)]
    assert lenguas == ["A", "A", "C"]


def test_se_pueden_elegir_otros_valores(volcado, tmp_path):
    entrada = volcado(('"202', "Q"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada),
                 "--salida", str(salida), "--estado", "BAJA", "--lengua", "C")

    fila = _leer(salida)[0]["fields"]
    assert fila["estado"] == "BAJA"
    assert fila["lengua"] == "C"


# --- Lo que NO hace ---

def test_no_toca_el_volcado_original(volcado, tmp_path):
    """Es la unica prueba de lo que decia el beta de verdad."""
    entrada = volcado(('"202', "Q"))
    original = entrada.read_text(encoding="utf-8")

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(tmp_path / "s.json"))

    assert entrada.read_text(encoding="utf-8") == original


def test_en_seco_no_escribe_nada(volcado, tmp_path):
    entrada = volcado(('"202', "Q"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida), "--dry-run")

    assert not salida.exists()


def test_se_niega_a_pisar_un_archivo_que_ya_existe(volcado, tmp_path):
    entrada = volcado(('"202', "Q"))
    salida = tmp_path / "saneado.json"
    salida.write_text("no me pises", encoding="utf-8")

    with pytest.raises(CommandError, match="ya existe"):
        call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    assert salida.read_text(encoding="utf-8") == "no me pises"


def test_no_toca_las_filas_que_no_son_afiliados(volcado, tmp_path):
    entrada = volcado(("ALTA", "A"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    filas = json.loads(salida.read_text(encoding="utf-8"))
    usuarios = [f for f in filas if f["model"] == "auth.user"]
    assert len(usuarios) == 1
    assert usuarios[0]["fields"]["username"] == "sov_uno"


# --- Lo que cuenta ---

def test_dice_cuantas_filas_ha_tocado(volcado, tmp_path, capsys):
    """La constancia es el motivo de que esto sea un comando: se esta fijando
    por asuncion el estado de afiliacion de gente."""
    entrada = volcado(('"202', "Q"), ('"201', "A"), ("ALTA", "A"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    texto = capsys.readouterr().out
    assert "2" in texto, "no dice cuantos estados ha fijado"
    assert "ALTA" in texto


def test_avisa_de_que_es_una_asuncion(volcado, tmp_path, capsys):
    """Quien lo ejecute dentro de un ano tiene que ver que esto no recupera un
    dato: lo inventa segun un criterio."""
    entrada = volcado(('"202', "Q"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    texto = capsys.readouterr().out.lower()
    assert "asum" in texto or "asunción" in texto or "asuncion" in texto


def test_dice_a_que_sindicatos_afecta(volcado, tmp_path, capsys):
    """Si son tres, una llamada lo resuelve; si son treinta, es otra
    conversacion. Hay que poder verlo antes de decidir."""
    entrada = volcado(('"202', "A"))
    salida = tmp_path / "saneado.json"

    call_command("sanear_volcado_beta", str(entrada), "--salida", str(salida))

    assert "sindicato" in capsys.readouterr().out.lower()

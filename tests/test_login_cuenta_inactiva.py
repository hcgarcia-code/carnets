"""TDD: al que espera aprobación se le dice que espera, no que se equivoca.

`ModelBackend.user_can_authenticate` rechaza a los usuarios con
`is_active=False` ANTES de comprobar la contraseña, de modo que el formulario
nunca llega a `confirm_login_allowed` y cae en el error genérico. La pantalla
decía «Usuario o contraseña incorrectos» a quien los tenía correctos.

Pasó de verdad: `SUB_CGT` se registró el 31-08-2026 a las 09:43 y lo intentó a
las 09:44, 09:45 y 09:46. Dos intentos más y el limitador lo habría bloqueado
por insistir en algo que no dependía de él.

**La regla que fija este archivo**: el aviso solo se da si la contraseña es
CORRECTA. Darlo con solo acertar el nombre de usuario convertiría la pantalla en
un comprobador público de qué sindicatos están dados de alta —y qué sindicatos
usan el sistema es justo lo que el proyecto protege al escribir a cada uno por
separado en vez de meterlos a todos en el mismo `To:`.
"""

import json
import logging

import pytest
from django.contrib.auth.models import User

from gestion.auditoria import ACCIONES
from gestion.auth_views import INTENTOS_MAXIMOS
from gestion.models import PerfilSindicato

pytestmark = pytest.mark.django_db

CLAVE = "clave-larga-de-prueba-123"  # noqa: S105
AVISO = "no está activa"


@pytest.fixture
def auditoria(caplog):
    caplog.set_level(logging.INFO, logger="auditoria")

    def leer():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "auditoria"]

    return leer


def _sindicato(nombre="sub_cgt", activo=False):
    usuario = User.objects.create_user(nombre, email=f"{nombre}@ejemplo.es", password=CLAVE)
    usuario.is_active = activo
    usuario.save()
    PerfilSindicato.objects.create(usuario=usuario, nombre_identificativo=f"CGT {nombre}")
    return usuario


def _entrar(client, usuario="sub_cgt", clave=CLAVE):
    return client.post("/login/", {"username": usuario, "password": clave})


# --- Lo que sí se dice ---

def test_con_la_clave_correcta_se_explica_que_falta_aprobar(client):
    _sindicato()

    contenido = _entrar(client).content.decode()

    assert AVISO in contenido, (
        "sigue diciendo que las credenciales son incorrectas cuando son correctas"
    )


def test_el_aviso_no_le_manda_a_recuperar_la_contrasena(client):
    """Su contraseña está bien: mandarle a reponerla le hace perder el tiempo y
    gasta el cupo de reposiciones."""
    _sindicato()

    contenido = _entrar(client).content.decode()

    assert "Usuario o contraseña incorrectos" not in contenido


# --- Lo que NO se dice: sin comprobante de que la cuenta es suya ---

def test_con_la_clave_equivocada_no_se_revela_que_la_cuenta_existe(client):
    """Si bastara con acertar el usuario, cualquiera podría averiguar desde
    fuera qué sindicatos están dados de alta."""
    _sindicato()

    contenido = _entrar(client, clave="una-clave-que-no-es").content.decode()

    assert AVISO not in contenido
    assert "Usuario o contraseña incorrectos" in contenido


def test_un_usuario_que_no_existe_recibe_el_mensaje_de_siempre(client):
    contenido = _entrar(client, usuario="no_existe_este").content.decode()

    assert AVISO not in contenido
    assert "Usuario o contraseña incorrectos" in contenido


def test_una_cuenta_activa_con_clave_mala_recibe_el_mensaje_de_siempre(client):
    _sindicato(activo=True)

    contenido = _entrar(client, clave="una-clave-que-no-es").content.decode()

    assert AVISO not in contenido


def test_una_cuenta_activa_entra_con_normalidad(client):
    _sindicato(activo=True)

    respuesta = _entrar(client)

    assert respuesta.status_code == 302, "el camino normal no debe haberse tocado"


# --- Auditoría y límite ---

def test_se_registra_como_cuenta_inactiva_y_no_como_fallo_de_credenciales(client, auditoria):
    """Tres `login.fallido` de un sindicato que espera aprobación parecen un
    ataque en el registro. Son otra cosa y deben poder distinguirse."""
    _sindicato()

    _entrar(client)

    acciones = [r["accion"] for r in auditoria()]
    assert ACCIONES.LOGIN_CUENTA_INACTIVA in acciones
    assert ACCIONES.LOGIN_FALLIDO not in acciones


def test_el_intento_sigue_contando_para_el_limite(client):
    """El limitador no distingue casos a propósito: cada POST que no entra
    cuenta. Complicarlo es lo que abrió el agujero del login del admin."""
    _sindicato()

    for _ in range(INTENTOS_MAXIMOS):
        _entrar(client)

    assert _entrar(client).status_code == 429


def test_el_registro_no_guarda_la_contrasena_probada(client, auditoria):
    _sindicato()

    _entrar(client)

    assert CLAVE not in json.dumps(auditoria())

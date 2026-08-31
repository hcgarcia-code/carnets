"""TDD: el acceso al admin también tiene límite de intentos.

`LoginConLimiteDeIntentos` cubre `/login/`, la entrada de los sindicatos. El
admin se monta de serie (`path('admin/', admin.site.urls)`), así que su
formulario de acceso aceptaba intentos sin cuenta y sin dejar rastro: los
eventos `login.fallido` los emite la vista del sindicato, no la del admin.

El segundo factor sigue siendo la defensa principal —acertar la contraseña no
basta para entrar—, pero sin límite la única cuenta que ve los datos personales
en claro tiene un oráculo de contraseña ilimitado, y encima silencioso.

El contador se comparte con el login de sindicatos a propósito: es el mismo
modelo `User`, así que llevar dos cuentas separadas le daría al atacante el
doble de intentos sobre la misma credencial.
"""

import json
import logging

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from gestion.auditoria import ACCIONES
from gestion.auth_views import INTENTOS_MAXIMOS

pytestmark = pytest.mark.django_db

URL_ADMIN_LOGIN = "/admin/login/"
CLAVE_BUENA = "clave-larga-de-prueba-123"  # noqa: S105


@pytest.fixture
def auditoria(caplog):
    caplog.set_level(logging.INFO, logger="auditoria")

    def leer():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "auditoria"]

    return leer


def _superusuario(nombre="jefa"):
    return User.objects.create_superuser(nombre, f"{nombre}@ejemplo.es", CLAVE_BUENA)


def _intentar(client, username="jefa", password="incorrecta"):  # noqa: S107
    return client.post(URL_ADMIN_LOGIN, {"username": username, "password": password})


def test_el_login_del_admin_bloquea_tras_agotar_los_intentos(client):
    _superusuario()

    for numero in range(INTENTOS_MAXIMOS):
        respuesta = _intentar(client)
        assert respuesta.status_code == 200, f"el intento {numero + 1} no debía bloquearse todavía"

    assert _intentar(client).status_code == 429


def test_el_bloqueo_del_admin_queda_en_el_registro_de_auditoria(client, auditoria):
    _superusuario()

    for _ in range(INTENTOS_MAXIMOS + 1):
        _intentar(client)

    bloqueos = [r for r in auditoria() if r["accion"] == ACCIONES.LOGIN_BLOQUEADO]
    assert bloqueos, "un bloqueo del admin es lo primero que se mira al investigar un incidente"
    assert bloqueos[0]["vista"] == "admin", "hay que poder distinguirlo del login de sindicatos"


def test_cada_intento_fallido_del_admin_queda_registrado(client, auditoria):
    _superusuario()

    _intentar(client)

    fallidos = [r for r in auditoria() if r["accion"] == ACCIONES.LOGIN_FALLIDO]
    assert len(fallidos) == 1
    assert fallidos[0]["vista"] == "admin"
    assert fallidos[0]["usuario"] == "jefa"


def test_el_registro_del_admin_no_guarda_la_contrasena_probada(client, auditoria):
    _superusuario()
    secreta = "ClaveQueNoDebeAparecer-999"  # noqa: S105

    _intentar(client, password=secreta)

    assert secreta not in json.dumps(auditoria())


def test_el_contador_se_comparte_con_el_login_de_sindicatos(client):
    """El mismo usuario en las dos puertas es la misma credencial: agotar el
    límite en una debe cerrar la otra, o el atacante tiene el doble de tiros."""
    _superusuario()

    for _ in range(INTENTOS_MAXIMOS):
        client.post("/login/", {"username": "jefa", "password": "incorrecta"})

    assert _intentar(client).status_code == 429


def test_el_limite_es_por_usuario_y_no_tumba_a_los_demas(client):
    """Bloquear por IP a secas dejaría fuera a un administrador legítimo que
    comparta salida a internet con quien está probando contra otra cuenta."""
    _superusuario("jefa")
    _superusuario("otra")

    for _ in range(INTENTOS_MAXIMOS + 1):
        _intentar(client, username="jefa")

    assert _intentar(client, username="otra").status_code == 200


def test_tener_sesion_de_otra_cuenta_no_salta_el_limite(client, auditoria):
    """Regresión de un agujero real: el límite miraba `request.user`.

    Quien envía el formulario puede traer ya sesión de OTRA cuenta —basta una
    de sindicato corriente, sin staff ni permisos—, y entonces
    `is_authenticated` salía cierto pasara lo que pasara con las credenciales
    tecleadas. El contador no subía y la auditoría no escribía: intentos
    ilimitados y silenciosos contra la única cuenta que descifra datos
    personales.
    """
    _superusuario()
    User.objects.create_user("sindicato_cualquiera", password="clave-larga-123")  # noqa: S106
    client.post("/login/", {"username": "sindicato_cualquiera", "password": "clave-larga-123"})

    codigos = [_intentar(client).status_code for _ in range(INTENTOS_MAXIMOS + 1)]

    assert 429 in codigos, "con sesión de otra cuenta se tantea sin límite"
    fallidos = [r for r in auditoria() if r["accion"] == ACCIONES.LOGIN_FALLIDO]
    assert fallidos, "y además sin dejar rastro en la auditoría"


def test_un_rechazo_de_csrf_no_gasta_el_cupo_del_administrador(client, auditoria):
    """Un 403 no llega a comprobar credenciales. Contarlo dejaría que una
    petición forzada desde otro sitio dejara al administrador fuera."""
    from django.test import Client

    _superusuario()
    estricto = Client(enforce_csrf_checks=True)

    for _ in range(INTENTOS_MAXIMOS + 1):
        respuesta = estricto.post(
            URL_ADMIN_LOGIN, {"username": "jefa", "password": "incorrecta"},
        )
        assert respuesta.status_code == 403

    # El cupo sigue intacto para quien sí manda el token.
    assert _intentar(client).status_code == 200
    assert not [r for r in auditoria() if r["accion"] == ACCIONES.LOGIN_BLOQUEADO]


def test_la_pantalla_de_acceso_del_admin_se_sigue_viendo(client):
    """El límite solo mira los POST: un GET nunca debe devolver 429."""
    assert client.get(URL_ADMIN_LOGIN).status_code == 200


def test_el_segundo_factor_sigue_exigiendose_despues_del_cambio(client):
    """Regresión: envolver el login no debe desactivar django-otp."""
    usuario = _superusuario()
    client.force_login(usuario)  # autentica pero NO verifica el segundo factor

    assert client.get("/admin/gestion/afiliado/").status_code != 200


def test_el_sitio_del_admin_conserva_la_url_de_login(client):
    assert reverse("admin:login") == URL_ADMIN_LOGIN

"""TDD: una sola forma de saber desde dónde llega una petición.

El proyecto tenía dos, y ninguna acertaba detrás del proxy de PythonAnywhere:

- `REMOTE_ADDR` a secas (limitadores de login, alta y reposición, y auditoría).
  El razonamiento escrito era correcto —`X-Forwarded-For` la pone el cliente y
  es falsificable— pero no aplica detrás de un proxy que REESCRIBE la cabecera.
  En producción, `REMOTE_ADDR` valía siempre `10.0.0.110`, el balanceador:
  el limitador de reposición, que se clava solo en la IP, pasó a ser de cinco
  peticiones cada cuarto de hora **para todo el sitio**, y el campo `ip` de la
  auditoría decía lo mismo en todas las líneas.

- `X-Forwarded-For` tomando la PRIMERA entrada, en `acuerdo_legal`. Esa es la
  que el cliente puede escribir: si el proxy añade la real detrás, lo que se
  guardaba como constancia de la firma del acuerdo era un valor elegido por
  quien firma.

La regla que fija este archivo: la cabecera solo se cree si la petición viene de
un proxy declarado en `PROXIES_DE_CONFIANZA`, y dentro de ella se recorre de
DERECHA A IZQUIERDA. La última entrada la pone el proxy en el que confiamos; las
de la izquierda puede haberlas escrito el cliente.
"""

import pytest
from django.test import RequestFactory

from gestion.ip import ip_real

PROXY = "10.0.0.110"
CLIENTE = "85.50.4.249"


def _peticion(remote_addr, xff=None):
    peticion = RequestFactory().get("/")
    peticion.META["REMOTE_ADDR"] = remote_addr
    if xff is not None:
        peticion.META["HTTP_X_FORWARDED_FOR"] = xff
    return peticion


# --- Sin proxies declarados: la cabecera no vale nada ---

def test_sin_proxies_declarados_se_ignora_la_cabecera(settings):
    """Comportamiento por defecto y en local: el de antes, que es el seguro."""
    settings.PROXIES_DE_CONFIANZA = []

    assert ip_real(_peticion(CLIENTE, xff="1.2.3.4")) == CLIENTE


def test_una_peticion_directa_no_puede_falsear_su_origen(settings):
    """Quien llega sin pasar por nuestro proxy no puede elegir qué IP se anota,
    por mucho que mande la cabecera."""
    settings.PROXIES_DE_CONFIANZA = [PROXY]

    assert ip_real(_peticion("198.51.100.9", xff="1.2.3.4")) == "198.51.100.9"


# --- Detrás del proxy: se lee la cabecera, por la derecha ---

def test_detras_del_proxy_se_lee_la_ip_real(settings):
    settings.PROXIES_DE_CONFIANZA = [PROXY]

    assert ip_real(_peticion(PROXY, xff=CLIENTE)) == CLIENTE


def test_una_cabecera_forjada_por_el_cliente_no_gana(settings):
    """El caso que hace que se lea por la derecha: el cliente manda su propia
    cabecera y el proxy le añade detrás la IP real de la conexión."""
    settings.PROXIES_DE_CONFIANZA = [PROXY]

    assert ip_real(_peticion(PROXY, xff=f"1.2.3.4, {CLIENTE}")) == CLIENTE


def test_se_saltan_los_proxies_intermedios(settings):
    """Con varios saltos nuestros, la IP del cliente es la última que no es
    ninguno de ellos."""
    settings.PROXIES_DE_CONFIANZA = [PROXY, "10.0.0.5"]

    assert ip_real(_peticion(PROXY, xff=f"{CLIENTE}, 10.0.0.5")) == CLIENTE


def test_se_admite_un_rango_en_notacion_cidr(settings):
    """PythonAnywhere no garantiza una IP fija de balanceador."""
    settings.PROXIES_DE_CONFIANZA = ["10.0.0.0/8"]

    assert ip_real(_peticion("10.0.0.207", xff=CLIENTE)) == CLIENTE


# --- Casos límite: nunca deben reventar ---

def test_sin_cabecera_se_usa_la_conexion(settings):
    settings.PROXIES_DE_CONFIANZA = [PROXY]

    assert ip_real(_peticion(PROXY)) == PROXY


def test_una_entrada_ilegible_se_descarta(settings):
    """La cabecera la escribe quien quiera: puede traer cualquier cosa."""
    settings.PROXIES_DE_CONFIANZA = [PROXY]

    assert ip_real(_peticion(PROXY, xff=f"{CLIENTE}, no-es-una-ip")) == CLIENTE


def test_una_cabecera_entera_ilegible_cae_a_la_conexion(settings):
    settings.PROXIES_DE_CONFIANZA = [PROXY]

    assert ip_real(_peticion(PROXY, xff="basura, mas basura")) == PROXY


def test_si_todo_son_proxies_se_usa_la_conexion(settings):
    settings.PROXIES_DE_CONFIANZA = [PROXY, "10.0.0.5"]

    assert ip_real(_peticion(PROXY, xff="10.0.0.5")) == PROXY


def test_sin_peticion_no_hay_ip():
    assert ip_real(None) is None


def test_un_proxy_mal_escrito_en_la_configuracion_no_tumba_la_aplicacion(settings):
    """Un dedazo en el .env no puede dejar el sitio sin servir: se ignora esa
    entrada y se sigue con las demás."""
    settings.PROXIES_DE_CONFIANZA = ["esto-no-es-una-ip", PROXY]

    assert ip_real(_peticion(PROXY, xff=CLIENTE)) == CLIENTE


def test_una_cabecera_desmesurada_no_se_recorre_entera(settings):
    """La cabecera la elige el cliente: sin tope, una petición puede obligar a
    recorrer megabytes en cada acceso."""
    settings.PROXIES_DE_CONFIANZA = [PROXY]
    cadena = ", ".join(["10.0.0.5"] * 200) + f", {CLIENTE}"

    # Se lee por la derecha, así que la IP real —que va al final— se encuentra
    # antes de agotar el tope.
    assert ip_real(_peticion(PROXY, xff=cadena)) == CLIENTE


# --- Que los sitios que la necesitan la usen de verdad ---

@pytest.mark.django_db
def test_la_auditoria_registra_la_ip_del_cliente(settings, caplog):
    import json
    import logging

    from gestion.auditoria import ACCIONES, registrar

    settings.PROXIES_DE_CONFIANZA = [PROXY]
    caplog.set_level(logging.INFO, logger="auditoria")

    registrar(ACCIONES.LOGIN_FALLIDO, peticion=_peticion(PROXY, xff=CLIENTE), usuario="x")

    registro = json.loads(caplog.records[-1].getMessage())
    assert registro["ip"] == CLIENTE, "sin esto, todas las líneas dicen la IP del proxy"


@pytest.mark.django_db
def test_el_limite_de_reposicion_es_por_cliente_y_no_global(client, settings):
    """El fallo que se vio en producción: con la IP del proxy en todas las
    peticiones, el cupo de reposiciones era de cinco cada cuarto de hora para
    TODO el sitio. Con 51 sindicatos avisados de una dirección nueva, el sexto
    que pidiera su contraseña se llevaba un 429 sin haber hecho nada."""
    from gestion.auth_views import PETICIONES_RECUPERACION_MAXIMAS

    settings.PROXIES_DE_CONFIANZA = [PROXY]

    # Un cliente agota su cupo.
    for _ in range(PETICIONES_RECUPERACION_MAXIMAS + 1):
        respuesta = client.post(
            "/recuperar-password/", {"email": "uno@ejemplo.es"},
            REMOTE_ADDR=PROXY, HTTP_X_FORWARDED_FOR="203.0.113.1",
        )
    assert respuesta.status_code == 429

    # Otro cliente distinto no debe verse afectado.
    respuesta = client.post(
        "/recuperar-password/", {"email": "otro@ejemplo.es"},
        REMOTE_ADDR=PROXY, HTTP_X_FORWARDED_FOR="203.0.113.2",
    )
    assert respuesta.status_code != 429


@pytest.mark.django_db
def test_la_firma_del_acuerdo_no_guarda_una_ip_elegida_por_quien_firma(client, settings):
    """`ip_aceptacion` es la constancia de un consentimiento. Tomando la primera
    entrada de la cabecera, la escribía el propio firmante."""
    from django.contrib.auth.models import User

    from gestion.models import PerfilSindicato

    settings.PROXIES_DE_CONFIANZA = [PROXY]
    usuario = User.objects.create_user("sindicato_firma", password="clave-larga-123")  # noqa: S106
    client.force_login(usuario)

    client.post(
        "/acuerdo-legal/", {},
        REMOTE_ADDR=PROXY, HTTP_X_FORWARDED_FOR=f"9.9.9.9, {CLIENTE}",
    )

    perfil = PerfilSindicato.objects.get(usuario=usuario)
    assert perfil.acuerdo_aceptado
    assert perfil.ip_aceptacion == CLIENTE, "se ha guardado la IP que puso el firmante"

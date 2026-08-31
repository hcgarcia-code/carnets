"""TDD: una fila ilegible no puede tumbar el listado entero del admin.

`from_db_value` captura `ErrorDeDescifrado` para que un registro corrupto se
marque como ⟨no descifrable⟩ y las demás filas se sigan viendo. Pero
`descifrar()` solo convertía a `ErrorDeDescifrado` lo que fallase por
`InvalidTag`: si el cuerpo cifrado se trunca por debajo del tamaño del nonce,
`AESGCM.decrypt` lanza `ValueError` («Nonce must be between 8 and 128 bytes»),
que escapaba de `from_db_value` y devolvía un 500 en la única pantalla desde la
que se ven los datos — justo lo que ese `except` dice estar evitando.

No es alcanzable desde fuera: hace falta una fila ya corrupta en la base de
datos (una escritura a medias, un backup mal restaurado). Es robustez, no una
puerta abierta, y por eso el arreglo es ampliar el `except` y no otra cosa.
"""

import base64

import pytest
from django.contrib.auth.models import User
from django.db import connection

from gestion.crypto import (
    MARCA_NO_DESCIFRABLE,
    ErrorDeDescifrado,
    TextoNoDescifrable,
    cifrar,
    descifrar,
)
from gestion.models import Afiliado

pytestmark = pytest.mark.django_db

_CLAVE_PRUEBAS = base64.b64encode(bytes(range(32))).decode()


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{_CLAVE_PRUEBAS}"


def _cuerpo_truncado(texto="Aurora Beltrán", bytes_utiles=5):
    """Un valor con el formato correcto pero el cuerpo cortado.

    Conserva `v1$<id_de_clave>$` para que llegue hasta AESGCM: si se rompiera
    antes, lo pararía la comprobación de formato y no probaríamos nada.
    """
    version, clave_id, _ = cifrar(texto).split("$")
    return f"{version}${clave_id}${base64.b64encode(bytes(bytes_utiles)).decode()}"


def _crear_afiliado():
    usuario = User.objects.create_user("sindicato_roto", password="clave-larga-123")  # noqa: S106
    afiliado = Afiliado(
        sindicato_usuario=usuario,
        confederacion_territorial="01",
        federacion_local="12345",
        federacion_sectorial="02",
        sindicato_codigo="003",
        num_afiliado="123456",
        nombre_apellidos="Aurora Beltrán",
        lengua="A",
        estado="ALTA",
    )
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


def test_un_cuerpo_truncado_se_reporta_como_error_de_descifrado():
    with pytest.raises(ErrorDeDescifrado):
        descifrar(_cuerpo_truncado())


def test_una_fila_truncada_en_la_bd_no_tumba_la_lectura():
    afiliado = _crear_afiliado()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE gestion_afiliado SET nombre_apellidos = %s WHERE id = %s",
            [_cuerpo_truncado(), afiliado.pk],
        )

    leido = Afiliado.objects.get(pk=afiliado.pk)

    assert leido.nombre_apellidos == MARCA_NO_DESCIFRABLE
    assert isinstance(leido.nombre_apellidos, TextoNoDescifrable)


def test_las_demas_filas_se_siguen_leyendo_con_una_corrupta():
    """El motivo de todo esto: que una fila rota no ciegue el resto del archivo."""
    roto = _crear_afiliado()
    sano = Afiliado.objects.create(
        sindicato_usuario=roto.sindicato_usuario,
        confederacion_territorial="01",
        federacion_local="12345",
        federacion_sectorial="02",
        sindicato_codigo="003",
        num_afiliado="654321",
        nombre_apellidos="Nombre Legible",
        lengua="A",
        estado="ALTA",
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE gestion_afiliado SET nombre_apellidos = %s WHERE id = %s",
            [_cuerpo_truncado(), roto.pk],
        )

    nombres = {a.pk: a.nombre_apellidos for a in Afiliado.objects.all()}

    assert nombres[roto.pk] == MARCA_NO_DESCIFRABLE
    assert nombres[sano.pk] == "Nombre Legible"


def test_el_listado_del_admin_aguanta_una_fila_corrupta(client, entrar_en_el_admin):
    afiliado = _crear_afiliado()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE gestion_afiliado SET nombre_apellidos = %s WHERE id = %s",
            [_cuerpo_truncado(), afiliado.pk],
        )
    jefa = User.objects.create_superuser("jefa", "j@ejemplo.es", "clave-larga-123")  # noqa: S106
    entrar_en_el_admin(client, jefa)

    respuesta = client.get("/admin/gestion/afiliado/")

    assert respuesta.status_code == 200
    assert MARCA_NO_DESCIFRABLE in respuesta.content.decode()


def test_una_marca_ilegible_nunca_se_escribe_encima_del_dato_original():
    """Regresión de la garantía que ya existía: al guardar una fila leída como
    ilegible se destruiría el texto cifrado que todavía está ahí."""
    afiliado = _crear_afiliado()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE gestion_afiliado SET nombre_apellidos = %s WHERE id = %s",
            [_cuerpo_truncado(), afiliado.pk],
        )

    leido = Afiliado.objects.get(pk=afiliado.pk)
    with pytest.raises(ErrorDeDescifrado):
        leido.save()

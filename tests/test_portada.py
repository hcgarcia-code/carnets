"""La direccion principal tiene que llevar a algun sitio.

El beta tenia portada; el 2.0 nacio sin ella y la raiz devolvia 404. Quien
escribe la direccion a secas --que es lo que hace la gente-- se encontraba con
un error, y ni siquiera uno que le dijera adonde ir.

Es una pagina publica, sin sesion, asi que la ve cualquiera que pase por ahi:
lo unico que puede contener son los dos caminos de entrada. Ni nombres de
sindicatos, ni recuentos, ni nada que diga quien usa el sistema.
"""

import pytest
from django.contrib.auth.models import User

from gestion.models import PerfilSindicato


@pytest.mark.django_db
def test_la_raiz_responde(client):
    """Antes daba 404: la ruta no existia."""
    assert client.get("/").status_code == 200


@pytest.mark.django_db
def test_no_hace_falta_estar_dentro_para_verla(client):
    """Si exigiera sesion redirigiria al login, y entonces no seria una portada
    sino un rodeo."""
    respuesta = client.get("/")

    assert respuesta.status_code == 200
    assert "login" not in respuesta.headers.get("Location", "")


@pytest.mark.django_db
def test_lleva_a_los_dos_caminos_de_entrada(client):
    """Entrar y darse de alta. Son las dos unicas cosas que se pueden hacer sin
    cuenta, y el motivo de que la pagina exista."""
    contenido = client.get("/").content.decode()

    assert "/login/" in contenido, "falta el acceso"
    assert "/alta/" in contenido, "falta el alta de sindicatos"


@pytest.mark.django_db
def test_no_dice_quien_usa_el_sistema(client):
    """Una portada publica que enumere sindicatos o de recuentos convierte la
    direccion en un listado de quien esta afiliado a CGT, sin autenticarse.
    Es el mismo criterio por el que la recuperacion de contrasena no confirma
    si una direccion existe."""
    usuario = User.objects.create_user("sov_madrid", "a@ejemplo.es", "clave-larga-123")  # noqa: S106
    PerfilSindicato.objects.create(
        usuario=usuario, nombre_identificativo="SOV Madrid", persona_contacto="Ana Ejemplo",
    )

    contenido = client.get("/").content.decode()

    assert "SOV Madrid" not in contenido
    assert "sov_madrid" not in contenido
    assert "Ana Ejemplo" not in contenido


@pytest.mark.django_db
def test_lleva_la_politica_de_seguridad(client):
    """Es la pagina mas visitada y la unica que ve gente que no tiene cuenta:
    no puede quedarse fuera de la CSP por ser estatica."""
    politica = client.get("/").headers.get("Content-Security-Policy", "")

    assert "script-src 'self'" in politica

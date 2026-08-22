"""Configuración común de las pruebas."""

import pytest
from django.core.cache import cache
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice


@pytest.fixture
def entrar_en_el_admin():
    """Autentica al usuario Y le da por superado el segundo factor.

    Desde que el admin exige segundo factor (ver gestion/admin.py),
    `force_login` por sí solo ya no basta para pasar de la pantalla de acceso:
    autentica, pero deja al usuario sin verificar. Cualquier prueba que entre
    al admin por HTTP tiene que usar esto en su lugar.

    El síntoma cuando se olvida es engañoso: la petición devuelve 302 y la
    prueba falla diciendo que no se registró la auditoría, cuando lo que pasa
    es que nunca se llegó a la vista.

    Es un fixture y no una función suelta porque `tests/` no está en el
    pythonpath (ver pyproject.toml): importarla desde otro archivo de pruebas
    daría ModuleNotFoundError.
    """
    def _entrar(client, usuario):
        dispositivo = TOTPDevice.objects.create(
            user=usuario, name="prueba", confirmed=True,
        )
        client.force_login(usuario)
        sesion = client.session
        sesion[DEVICE_ID_SESSION_KEY] = dispositivo.persistent_id
        sesion.save()
        return dispositivo

    return _entrar


@pytest.fixture(autouse=True)
def cache_limpia():
    """Vacía la caché entre pruebas.

    Los limitadores de intentos (login y alta) llevan la cuenta en la caché,
    y la caché en memoria de Django vive en el proceso, no en la base de
    datos: a diferencia de las tablas, pytest-django no la revierte al acabar
    cada prueba. Sin esto, los tests que agotan el límite a propósito dejan el
    contador saturado para todo lo que se ejecute después, y la siguiente
    prueba que toque /login/ o /alta/ recibe un 429 por algo que no hizo.

    El síntoma es de los que más tiempo hacen perder: la prueba nueva falla
    sola, pasa si se ejecuta aislada, y el fallo cambia de sitio al reordenar
    los archivos.
    """
    cache.clear()
    yield
    cache.clear()

"""La configuración de producción se comprueba antes de desplegar.

Los dos limitadores de intentos (login y alta) llevan su contador en la caché.
Eso convierte al backend de caché en un control de seguridad: con la caché en
memoria del proceso —el defecto de Django— cada worker de gunicorn lleva su
propio contador, así que el límite real deja de ser 5 intentos y pasa a ser 5
por worker, y además se reinicia en cada recarga. La protección contra fuerza
bruta se evapora justo al desplegar, en silencio y sin que nada falle.

Se comprueba como check de despliegue (`manage.py check --deploy`), que es
donde el script de despliegue ya mira, y no al arrancar: los checks marcados
con deploy=True no se ejecutan ni en el arranque normal ni en las pruebas
—donde DEBUG es False y un guard de arranque las tumbaría todas—.
"""

import pytest
from django.core.checks import Error
from django.test import override_settings

from gestion.checks import CACHE_NO_COMPARTIDA, comprobar_cache_compartida

LOCMEM = "django.core.cache.backends.locmem.LocMemCache"
DUMMY = "django.core.cache.backends.dummy.DummyCache"
REDIS = "django.core.cache.backends.redis.RedisCache"
BASE_DE_DATOS = "django.core.cache.backends.db.DatabaseCache"


def _con_backend(ruta):
    return override_settings(CACHES={"default": {"BACKEND": ruta}})


@pytest.mark.parametrize("backend", [LOCMEM, DUMMY])
def test_rechaza_las_caches_que_no_se_comparten_entre_procesos(backend):
    with _con_backend(backend):
        errores = comprobar_cache_compartida(None)

    assert len(errores) == 1
    # Error y no Warning: un aviso no detiene el despliegue por sí solo.
    assert isinstance(errores[0], Error)
    assert errores[0].id == CACHE_NO_COMPARTIDA


@pytest.mark.parametrize("backend", [REDIS, BASE_DE_DATOS])
def test_acepta_las_caches_compartidas(backend):
    with _con_backend(backend):
        assert comprobar_cache_compartida(None) == []


def test_el_error_explica_la_consecuencia_real_no_solo_el_sintoma():
    """El mensaje tiene que decir QUÉ se rompe, no solo qué ajuste falta.

    Quien lo lea durante un despliegue no tiene por qué saber que la caché
    sostiene los limitadores: si el texto solo dice "usa Redis", lo más
    probable es que lo salte por considerarlo una optimización.
    """
    with _con_backend(LOCMEM):
        error = comprobar_cache_compartida(None)[0]

    texto = f"{error.msg} {error.hint}".lower()
    assert "intentos" in texto
    assert "worker" in texto


def test_el_check_esta_registrado_como_check_de_despliegue():
    """Si no está registrado con deploy=True, `check --deploy` no lo ejecuta
    y el script de despliegue nunca se entera."""
    from django.core.checks.registry import registry

    assert comprobar_cache_compartida in registry.get_checks(include_deployment_checks=True)
    assert comprobar_cache_compartida not in registry.get_checks(include_deployment_checks=False)

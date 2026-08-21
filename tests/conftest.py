"""Configuración común de las pruebas."""

import pytest
from django.core.cache import cache


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

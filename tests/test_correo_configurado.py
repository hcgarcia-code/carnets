"""El correo saliente tiene que estar configurado, o falla en silencio.

Django trae dos valores por defecto que no fallan nunca y no funcionan nunca:
`DEFAULT_FROM_EMAIL = 'webmaster@localhost'` y `ADMINS = []`. Con el primero,
los correos de reposicion de contrasena salen con un remitente que ningun
servidor acepta. Con el segundo, `mail_admins()` --que es como avisa
`revisar_auditoria` de una racha de bloqueos o de una exportacion-- se ejecuta
sin error y no escribe a nadie.

Las dos cosas rompen algo que la documentacion da por hecho, y ninguna de las
dos se nota hasta que hace falta. Por eso se comprueban antes de desplegar.
"""

import pytest
from django.core.checks import run_checks
from django.core.checks.registry import registry

from gestion.checks import ADMINS_SIN_CONFIGURAR, REMITENTE_SIN_CONFIGURAR


def _comprobar(**ajustes):
    """Ejecuta solo las comprobaciones de despliegue, que es cuando aplican."""
    from django.test import override_settings

    with override_settings(**ajustes):
        return [str(m.id) for m in run_checks(include_deployment_checks=True)]


def test_el_remitente_por_defecto_de_django_bloquea_el_despliegue():
    """`webmaster@localhost` con un servidor SMTP configurado es la receta de
    'la reposicion de contrasena no llega y nadie sabe por que'."""
    fallos = _comprobar(
        EMAIL_HOST="smtp.ejemplo.es",
        DEFAULT_FROM_EMAIL="webmaster@localhost",
        ADMINS=[("Admin", "admin@ejemplo.es")],
    )

    assert REMITENTE_SIN_CONFIGURAR in fallos


def test_un_remitente_de_verdad_pasa():
    fallos = _comprobar(
        EMAIL_HOST="smtp.ejemplo.es",
        DEFAULT_FROM_EMAIL="soporte-carnets@cgt.org.es",
        ADMINS=[("Admin", "admin@ejemplo.es")],
    )

    assert REMITENTE_SIN_CONFIGURAR not in fallos


def test_sin_servidor_de_correo_no_se_queja_del_remitente():
    """En local no hay SMTP y los correos van a la consola: exigir un remitente
    real ahi seria ruido en cada `check`."""
    fallos = _comprobar(
        EMAIL_HOST="",
        DEFAULT_FROM_EMAIL="webmaster@localhost",
        ADMINS=[],
    )

    assert REMITENTE_SIN_CONFIGURAR not in fallos


def test_sin_ADMINS_las_alertas_no_llegan_a_nadie():
    """`revisar_auditoria` avisa por `mail_admins`. Con ADMINS vacio se ejecuta
    igual, no da error, y el aviso no sale: la deteccion documentada en el
    manual de administrador (5.4) no existe."""
    fallos = _comprobar(
        EMAIL_HOST="smtp.ejemplo.es",
        DEFAULT_FROM_EMAIL="soporte-carnets@cgt.org.es",
        ADMINS=[],
    )

    assert ADMINS_SIN_CONFIGURAR in fallos


def test_con_ADMINS_configurado_pasa():
    fallos = _comprobar(
        EMAIL_HOST="smtp.ejemplo.es",
        DEFAULT_FROM_EMAIL="soporte-carnets@cgt.org.es",
        ADMINS=[("Admin", "admin@ejemplo.es")],
    )

    assert ADMINS_SIN_CONFIGURAR not in fallos


def test_las_comprobaciones_solo_corren_al_desplegar():
    """Registradas con deploy=True: no deben molestar en `manage.py runserver`
    ni durante las pruebas."""
    ids = {getattr(f, "__name__", "") for f in registry.get_checks(include_deployment_checks=False)}

    assert "comprobar_remitente_de_correo" not in ids
    assert "comprobar_destinatarios_de_alertas" not in ids


@pytest.mark.django_db
def test_el_proyecto_trae_un_remitente_por_defecto_utilizable(settings):
    """Aunque nadie ponga nada en el .env, el remitente no debe ser el de
    Django: la direccion de soporte es publica y sirve."""
    assert "localhost" not in settings.DEFAULT_FROM_EMAIL
    assert "@" in settings.DEFAULT_FROM_EMAIL

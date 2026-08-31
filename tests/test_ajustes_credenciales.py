"""TDD: los dos ajustes de credenciales que estaban por omisión, no decididos.

1. `PASSWORD_RESET_TIMEOUT` no estaba definido, así que valía el de Django:
   **tres días**. La plantilla del correo (`password/correo.txt`) dice «El
   enlace caduca en unas horas y solo sirve una vez», de modo que el sistema
   afirmaba algo falso sobre el enlace que da acceso a una cuenta. Se arregla
   poniendo el ajuste, no cambiando el texto: un enlace de reposición vivo
   durante tres días en un buzón es una llave olvidada en la puerta.

2. `MinimumLengthValidator` iba sin `OPTIONS`, así que regía el mínimo de
   Django (8). En cuentas que custodian ficheros de afiliación sindical eso no
   es una decisión tomada, es una que no se tomó.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

PLANTILLA_CORREO = (
    Path(settings.BASE_DIR)
    / "gestion" / "templates" / "gestion" / "password" / "correo.txt"
)

UNA_HORA = 60 * 60


def _validador(nombre):
    for entrada in settings.AUTH_PASSWORD_VALIDATORS:
        if entrada["NAME"].endswith(nombre):
            return entrada
    raise AssertionError(f"{nombre} no está en AUTH_PASSWORD_VALIDATORS")


# --- Caducidad del enlace de reposición ---

def test_el_enlace_de_reposicion_caduca_en_horas_no_en_dias():
    assert settings.PASSWORD_RESET_TIMEOUT <= 6 * UNA_HORA, (
        "con el valor por defecto de Django el enlace vive tres días"
    )
    assert settings.PASSWORD_RESET_TIMEOUT >= UNA_HORA, (
        "demasiado corto: el sindicato tiene que poder leer el correo y usarlo"
    )


def test_el_correo_y_el_ajuste_dicen_lo_mismo():
    """El correo promete «unas horas»: el ajuste tiene que sostener esa frase."""
    texto = PLANTILLA_CORREO.read_text(encoding="utf-8")

    assert "caduca en unas horas" in texto, (
        "si se cambia el texto del correo, hay que revisar PASSWORD_RESET_TIMEOUT"
    )
    horas = settings.PASSWORD_RESET_TIMEOUT / UNA_HORA
    assert 1 <= horas <= 6, f"«unas horas» no describe {horas} horas"


# --- Longitud mínima de contraseña ---

def test_la_longitud_minima_de_contrasena_esta_decidida():
    validador = _validador("MinimumLengthValidator")

    assert "OPTIONS" in validador, "sin OPTIONS rige el mínimo de Django (8)"
    assert validador["OPTIONS"]["min_length"] >= 12


@pytest.mark.django_db
def test_una_contrasena_corta_se_rechaza():
    with pytest.raises(ValidationError):
        validate_password("Abcde-123")  # 9 caracteres  # noqa: S106


@pytest.mark.django_db
def test_una_contrasena_larga_y_razonable_se_acepta():
    validate_password("caracola-verde-sindical-42")  # noqa: S106


@pytest.mark.django_db
def test_el_alta_de_un_sindicato_rechaza_una_contrasena_corta(client):
    """La comprobación que de verdad importa: el alta es pública."""
    respuesta = client.post("/alta/", {
        "username": "sov_prueba",
        "email": "sov@ejemplo.es",
        "nombre_identificativo": "CGT SOV Prueba",
        "persona_contacto": "Marta Ruiz",
        "password1": "Abcde-12345",   # 11 caracteres  # noqa: S106
        "password2": "Abcde-12345",   # noqa: S106
    })

    from django.contrib.auth.models import User
    assert not User.objects.filter(username="sov_prueba").exists()
    assert respuesta.status_code == 200


def test_los_validadores_de_contrasena_no_estan_duplicados():
    nombres = [v["NAME"] for v in settings.AUTH_PASSWORD_VALIDATORS]

    assert len(nombres) == len(set(nombres)), f"validadores repetidos: {nombres}"

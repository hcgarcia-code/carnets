"""El nombre de usuario no puede ser un documento de identidad.

En el volcado del beta aparecieron dos cuentas cuyo nombre de usuario es un DNI.
El nombre de usuario **se escribe en el registro de auditoria**: cada
`login.correcto`, cada `afiliados.cargados` lleva el campo `usuario`. Con una
cuenta asi, una linea del registro dice que el titular de un DNI concreto ha
cargado afiliacion sindical, que es dato de categoria especial (Art. 9), en un
archivo que el proyecto declara libre de datos personales.

El alta es autoservicio y publica, asi que sin esto vuelve a pasar. Se valida en
el formulario --el punto por donde entra-- y no en el modelo, para poder
explicar el motivo a quien lo esta escribiendo.

Las dos cuentas heredadas del beta hay que renombrarlas a mano, avisando antes
al sindicato: renombrar a alguien le cambia la forma de entrar.
"""

import pytest
from django.contrib.auth.models import User

from gestion.forms import RegistroSindicatoForm

DATOS_BASE = {
    "email": "sindicato@ejemplo.es",
    "nombre_identificativo": "CGT Rama Ejemplo",
    "persona_contacto": "Ana Ejemplo",
    "password1": "una-clave-larga-2026",
    "password2": "una-clave-larga-2026",
}


def _formulario(username):
    return RegistroSindicatoForm(data={**DATOS_BASE, "username": username})


@pytest.mark.django_db
@pytest.mark.parametrize("documento", [
    "24290790F",     # DNI, el formato que aparecio en el beta
    "25950553K",
    "12345678Z",
    "12345678z",     # en minuscula cuenta igual
    "X1234567L",     # NIE
    "Y7654321M",
    "Z1111111S",
    "x1234567l",
])
def test_rechaza_un_documento_de_identidad(documento):
    formulario = _formulario(documento)

    assert not formulario.is_valid(), f"{documento} deberia rechazarse"
    assert "username" in formulario.errors


@pytest.mark.django_db
def test_el_mensaje_explica_por_que(caplog):
    """Un 'nombre de usuario no valido' a secas hace que la persona pruebe otra
    variante del mismo DNI. Tiene que decir que ponga el sindicato."""
    formulario = _formulario("12345678Z")
    formulario.is_valid()

    mensaje = " ".join(formulario.errors["username"]).lower()

    assert "documento" in mensaje or "dni" in mensaje
    assert "sindicato" in mensaje


@pytest.mark.django_db
@pytest.mark.parametrize("username", [
    "cgt_sov_avila",
    "SOVCGTLEON",
    "hosteleriabcn",
    "federaciointercomarcallleida",
    "sap_mallorca",
    "SAYSEP_SORIA",
    "24290790",       # ocho digitos sin letra no es un DNI
    "2429079F",       # siete digitos y letra tampoco
    "243290790FF",
    "cgt2024",
])
def test_no_estorba_a_los_nombres_normales(username):
    """La validacion no puede llevarse por delante los nombres que ya se usan:
    estos salen del censo real del beta."""
    formulario = _formulario(username)

    assert formulario.is_valid(), f"{username} deberia valer: {formulario.errors}"


@pytest.mark.django_db
def test_un_alta_normal_sigue_funcionando():
    """Que la validacion nueva no haya roto el alta entera."""
    formulario = _formulario("cgt_rama_nueva")

    assert formulario.is_valid(), formulario.errors
    usuario = formulario.save()

    assert User.objects.filter(username="cgt_rama_nueva").exists()
    assert not usuario.is_active, "el alta sigue creando la cuenta inactiva"

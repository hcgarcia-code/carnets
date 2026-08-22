"""El admin exige un segundo factor, y hay forma de darlo de alta sin quedarse fuera.

La cuenta de administrador es la única que ve los datos personales descifrados:
el resto del sistema está construido para no poder (la imprenta consulta con
`.values()` sin los nombres, el registro de auditoría no los escribe, la base de
datos los guarda cifrados). Todo ese trabajo se apoya en una contraseña, así que
una contraseña robada entrega el archivo entero de afiliación sindical.

El segundo factor es lo que impide que una credencial filtrada baste. Se aplica
sobre el sitio del admin —no sobre el login de sindicatos— porque es ahí donde
se descifra.
"""

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice
from io import StringIO

URL_ADMIN = "/admin/gestion/afiliado/"


def _superusuario(nombre="jefa"):
    return User.objects.create_superuser(
        nombre, f"{nombre}@ejemplo.es", "clave-larga-de-prueba-123",  # noqa: S106
    )


def verificar_segundo_factor(client, usuario):
    """Deja la sesión como si el usuario acabara de pasar el segundo factor.

    Lo necesita cualquier prueba que entre al admin por HTTP: `force_login`
    autentica pero no verifica, y desde que el admin exige segundo factor eso
    ya no basta para pasar de la pantalla de acceso.
    """
    dispositivo = TOTPDevice.objects.create(user=usuario, name="prueba", confirmed=True)
    client.force_login(usuario)
    sesion = client.session
    sesion[DEVICE_ID_SESSION_KEY] = dispositivo.persistent_id
    sesion.save()
    return dispositivo


@pytest.mark.django_db
def test_una_contrasena_correcta_no_basta_para_entrar_al_admin(client):
    """El caso que justifica todo esto: credencial válida, pero robada."""
    usuario = _superusuario()
    client.force_login(usuario)

    respuesta = client.get(URL_ADMIN)

    assert respuesta.status_code != 200, (
        "Con solo la contraseña se está viendo el listado de afiliados: "
        "el segundo factor no se está aplicando."
    )


@pytest.mark.django_db
def test_con_el_segundo_factor_verificado_se_entra_con_normalidad(client):
    usuario = _superusuario()
    verificar_segundo_factor(client, usuario)

    assert client.get(URL_ADMIN).status_code == 200


@pytest.mark.django_db
def test_un_dispositivo_sin_confirmar_no_sirve(client):
    """Un alta a medias no debe dar acceso: si diera, bastaría con empezar
    el proceso de enrolamiento y abandonarlo."""
    usuario = _superusuario()
    TOTPDevice.objects.create(user=usuario, name="a medias", confirmed=False)
    client.force_login(usuario)

    assert client.get(URL_ADMIN).status_code != 200


@pytest.mark.django_db
def test_el_login_de_sindicatos_no_pide_segundo_factor(client):
    """Los sindicatos no descifran nada: exigirles 2FA sería un coste sin
    contrapartida, y la barrera haría que dejaran de usar la aplicación."""
    User.objects.create_user("sindicato", password="clave-larga-de-prueba-123")  # noqa: S106

    respuesta = client.post(
        "/login/", {"username": "sindicato", "password": "clave-larga-de-prueba-123"},
    )

    assert respuesta.status_code == 302, "debe entrar con usuario y contraseña"


# --- El comando de alta: sin él, activar el 2FA es quedarse fuera del admin ---

@pytest.mark.django_db
def test_el_comando_crea_un_dispositivo_utilizable():
    usuario = _superusuario()
    salida = StringIO()

    call_command("activar_2fa", usuario.username, stdout=salida)

    dispositivo = TOTPDevice.objects.get(user=usuario)
    assert dispositivo.confirmed, "sin confirmar no daría acceso"
    assert "otpauth://" in salida.getvalue(), "hay que poder darlo de alta en la app"


@pytest.mark.django_db
def test_la_salida_del_comando_es_solo_ascii():
    """La consola de Windows usa cp1252: un carácter fuera de ese juego aborta
    el comando entero con UnicodeEncodeError, y encima después de haber creado
    ya el dispositivo. Es la misma trampa que hubo que arreglar en
    preparar_pruebas."""
    usuario = _superusuario()
    salida = StringIO()

    call_command("activar_2fa", usuario.username, stdout=salida)

    salida.getvalue().encode("cp1252")  # revienta si se cuela algo no ASCII


@pytest.mark.django_db
def test_el_comando_avisa_si_el_usuario_no_existe():
    with pytest.raises(CommandError, match="no existe"):
        call_command("activar_2fa", "nadie")


@pytest.mark.django_db
def test_reejecutar_el_comando_reemplaza_el_dispositivo_anterior():
    """Es la salida cuando alguien pierde el teléfono: si el comando fallara
    por existir ya un dispositivo, la única vía sería tocar la base de datos."""
    usuario = _superusuario()
    call_command("activar_2fa", usuario.username, stdout=StringIO())
    primer_secreto = TOTPDevice.objects.get(user=usuario).key

    call_command("activar_2fa", usuario.username, stdout=StringIO())

    dispositivos = TOTPDevice.objects.filter(user=usuario)
    assert dispositivos.count() == 1, "el anterior debe quedar revocado, no acumularse"
    assert dispositivos.first().key != primer_secreto, "un teléfono perdido no debe seguir valiendo"

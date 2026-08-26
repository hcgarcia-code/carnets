"""Correo de contacto en las cuentas y recuperacion de contrasena.

Viene de migrar las cuentas del beta (carnetscgt.eu.pythonanywhere.com). Aquel
recogia en el alta el correo y el nombre de la persona que solicitaba, y tenia
un flujo de "he olvidado mi contrasena" en /recuperar-password/. Este proyecto
no tenia ninguna de las tres cosas.

Migrar las cuentas sin recuperarlas dejaria a la gente peor que antes: se les
ahorra repetir el alta, pero el primero que olvide su clave se queda fuera
hasta que un administrador se la reponga a mano. Y sin correo guardado no hay
siquiera a donde escribirle.

Anadir recuperacion de contrasena a un sistema con cuentas pendientes de
aprobacion y con segundo factor en el admin abre tres agujeros que no son
obvios, y que son la razon de la mitad de las pruebas de este archivo:

1. Una cuenta aun no aprobada no debe poder activarse por esta via.
2. Reponer la contrasena de un administrador no puede saltarse su segundo
   factor: si lo hiciera, el correo pasaria a ser la unica barrera del punto
   donde se descifran los datos.
3. Sin limite de peticiones, cualquiera puede inundar el buzon de un sindicato
   pidiendo reposiciones en su nombre.
"""

import re

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django_otp.plugins.otp_totp.models import TOTPDevice

URL_RECUPERAR = "/recuperar-password/"
CLAVE_ORIGINAL = "clave-original-de-prueba-123"  # noqa: S105
CLAVE_NUEVA = "clave-nueva-de-prueba-456"  # noqa: S105


def _sindicato(nombre="sindicato_beta", correo="sindicato@ejemplo.es", activo=True):
    usuario = User.objects.create_user(nombre, correo, CLAVE_ORIGINAL)
    usuario.is_active = activo
    usuario.save()
    return usuario


def _enlace_del_correo():
    """Extrae del correo enviado el enlace de reposicion."""
    encontrados = re.findall(r"https?://\S+", mail.outbox[0].body)
    return [u for u in encontrados if "/recuperar-password/" in u][0]


# --- El alta recoge correo y persona de contacto ---

@pytest.mark.django_db
def test_el_alta_pide_correo_y_persona_de_contacto(client):
    """Son los dos campos que el beta ya recogia. Sin el correo no hay
    recuperacion de contrasena posible."""
    respuesta = client.get("/alta/")

    contenido = respuesta.content.decode()
    assert "email" in contenido.lower()
    assert "persona" in contenido.lower() or "contacto" in contenido.lower()


@pytest.mark.django_db
def test_el_alta_guarda_correo_y_persona_de_contacto(client):
    client.post("/alta/", {
        "username": "sov_madrid",
        "password1": "clave-larga-y-buena-123",
        "password2": "clave-larga-y-buena-123",
        "email": "sov@ejemplo.es",
        "nombre_identificativo": "SOV Madrid",
        "persona_contacto": "Ana Ejemplo",
    })

    usuario = User.objects.get(username="sov_madrid")
    assert usuario.email == "sov@ejemplo.es"
    assert usuario.perfil.persona_contacto == "Ana Ejemplo"
    assert usuario.is_active is False, "el alta debe seguir requiriendo aprobacion"


@pytest.mark.django_db
def test_el_correo_es_obligatorio(client):
    """Opcional seria peor que no tenerlo: la mitad de las cuentas quedarian
    sin via de recuperacion y no se sabria cuales hasta que hiciera falta."""
    client.post("/alta/", {
        "username": "sin_correo",
        "password1": "clave-larga-y-buena-123",
        "password2": "clave-larga-y-buena-123",
        "nombre_identificativo": "Sin correo",
        "persona_contacto": "Quien sea",
    })

    assert not User.objects.filter(username="sin_correo").exists()


# --- Recuperacion de contrasena ---

@pytest.mark.django_db
def test_se_puede_recuperar_la_contrasena(client):
    """El caso que justifica todo esto."""
    _sindicato()

    client.post(URL_RECUPERAR, {"email": "sindicato@ejemplo.es"})

    assert len(mail.outbox) == 1

    # Django no acepta el POST en la URL del correo: al visitarla guarda el
    # token en la sesion y redirige a otra que termina en /set-password/. Hay
    # que seguir esa redireccion y enviar el formulario alli.
    enlace = _enlace_del_correo()
    pagina = client.get(enlace, follow=True)
    url_formulario = pagina.redirect_chain[-1][0]

    client.post(
        url_formulario,
        {"new_password1": CLAVE_NUEVA, "new_password2": CLAVE_NUEVA},
        follow=True,
    )

    usuario = User.objects.get(username="sindicato_beta")
    assert usuario.check_password(CLAVE_NUEVA), "la contrasena no se ha cambiado"


@pytest.mark.django_db
def test_una_cuenta_pendiente_de_aprobacion_no_recibe_correo(client):
    """El alta crea la cuenta inactiva a proposito, para que un administrador
    revise quien es antes de dejarle subir datos de afiliacion. Si la
    recuperacion de contrasena funcionara sobre cuentas inactivas, cualquiera
    podria darse de alta y usar este flujo para saltarse esa revision."""
    _sindicato(nombre="pendiente", correo="pendiente@ejemplo.es", activo=False)

    client.post(URL_RECUPERAR, {"email": "pendiente@ejemplo.es"})

    assert mail.outbox == [], "no debe enviarse correo a una cuenta sin aprobar"


@pytest.mark.django_db
def test_no_revela_si_una_direccion_esta_registrada(client):
    """Responder distinto para una direccion conocida y una desconocida
    convierte este formulario en un comprobador de quien esta afiliado a CGT,
    accesible sin autenticarse."""
    _sindicato(correo="existe@ejemplo.es")

    conocida = client.post(URL_RECUPERAR, {"email": "existe@ejemplo.es"}, follow=True)
    desconocida = client.post(URL_RECUPERAR, {"email": "nadie@ejemplo.es"}, follow=True)

    assert conocida.status_code == desconocida.status_code
    assert conocida.content == desconocida.content


@pytest.mark.django_db
def test_reponer_la_contrasena_no_da_acceso_al_admin_sin_segundo_factor(client):
    """La prueba mas importante del archivo.

    El admin es el unico sitio donde los datos se ven descifrados, y esta
    protegido con segundo factor precisamente para que una contrasena filtrada
    no baste. Si al reponer la contrasena por correo se entrara sin el segundo
    factor, el buzon del administrador pasaria a ser la unica barrera de todo
    el archivo de afiliacion.
    """
    jefa = User.objects.create_superuser("jefa", "jefa@ejemplo.es", CLAVE_ORIGINAL)
    TOTPDevice.objects.create(user=jefa, name="suyo", confirmed=True)
    client.force_login(jefa)  # autenticada, pero sin verificar el segundo factor

    respuesta = client.get("/admin/gestion/afiliado/")

    assert respuesta.status_code != 200, (
        "se entra al admin sin segundo factor: la reposicion por correo lo estaria "
        "puenteando"
    )


@pytest.mark.django_db
def test_hay_limite_de_peticiones_de_recuperacion(client):
    """Sin limite, cualquiera puede inundar el buzon de un sindicato pidiendo
    reposiciones a su nombre. Mismo criterio que el login y el alta."""
    _sindicato(correo="objetivo@ejemplo.es")

    codigos = []
    for _ in range(8):
        codigos.append(client.post(URL_RECUPERAR, {"email": "objetivo@ejemplo.es"}).status_code)

    assert 429 in codigos, f"no se corta nunca; codigos obtenidos: {codigos}"


@pytest.mark.django_db
def test_el_correo_no_lleva_datos_de_afiliacion(client):
    """El correo sale del ambito cifrado y viaja por servidores ajenos: no debe
    contener nada mas que lo justo para reponer la contrasena."""
    _sindicato(correo="sindicato@ejemplo.es")

    client.post(URL_RECUPERAR, {"email": "sindicato@ejemplo.es"})

    cuerpo = mail.outbox[0].body
    assert "afiliado" not in cuerpo.lower()
    assert CLAVE_ORIGINAL not in cuerpo, "jamas la contrasena en un correo"

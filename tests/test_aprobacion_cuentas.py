"""TDD: el sindicato se entera de que su cuenta ya está activa.

El circuito tenía dos silencios seguidos, y los dos se vieron en el registro de
producción del 31-08-2026 con la cuenta `SUB_CGT`:

1. **Al aprobar no se avisaba.** `aprobar_cuentas` hacía `update(is_active=True)`
   y nada más. El sindicato solo podía enterarse volviendo a probar por su
   cuenta, sin saber si tenía sentido intentarlo.

2. **Al intentar entrar tampoco.** `ModelBackend` rechaza a los usuarios con
   `is_active=False` ANTES de comprobar la contraseña, así que el formulario cae
   en el error genérico y la pantalla dice «Usuario o contraseña incorrectos» a
   quien los tiene correctos. `SUB_CGT` se registró a las 09:43 y lo intentó a
   las 09:44, 09:45 y 09:46: dos más y se habría bloqueado solo.

La regla del punto 2, que es la delicada: el aviso de «cuenta pendiente» solo se
da si la contraseña es CORRECTA. Darlo con solo acertar el usuario convertiría
la pantalla en un comprobador público de qué sindicatos están dados de alta, que
es justo lo que el proyecto evita al escribir a cada uno por separado en vez de
poner a todos en el mismo `To:`.
"""

import json
import logging

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.test import RequestFactory

from gestion.admin import UsuarioAdmin, aprobar_cuentas
from gestion.auditoria import ACCIONES
from gestion.models import PerfilSindicato

pytestmark = pytest.mark.django_db

CLAVE = "clave-larga-de-prueba-123"  # noqa: S105


@pytest.fixture
def auditoria(caplog):
    caplog.set_level(logging.INFO, logger="auditoria")

    def leer():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "auditoria"]

    return leer


def _sindicato(nombre="sov_avila", correo="sov@ejemplo.es", activo=False):
    usuario = User.objects.create_user(nombre, email=correo, password=CLAVE)
    usuario.is_active = activo
    usuario.save()
    PerfilSindicato.objects.create(
        usuario=usuario, nombre_identificativo=f"CGT {nombre}", persona_contacto="Marta Ruiz",
    )
    return usuario


def _aprobar(queryset, usuario_admin=None):
    peticion = RequestFactory().get("/admin/")
    peticion.user = usuario_admin or User.objects.create_superuser(
        "jefa", "j@ejemplo.es", CLAVE,
    )
    peticion.session = {}
    peticion._messages = FallbackStorage(peticion)  # noqa: SLF001
    aprobar_cuentas(UsuarioAdmin(User, AdminSite()), peticion, queryset)
    return peticion


# --- Aprobar sigue haciendo lo que hacía ---

def test_aprobar_activa_la_cuenta():
    sindicato = _sindicato()

    _aprobar(User.objects.filter(pk=sindicato.pk))

    sindicato.refresh_from_db()
    assert sindicato.is_active is True


def test_no_se_reavisa_a_quien_ya_estaba_activo():
    """Aprobar en bloque una selección donde ya hay cuentas activas no debe
    escribirles otra vez: ya recibieron el suyo cuando les tocó."""
    _sindicato("ya_dentro", activo=True)
    nuevo = _sindicato("recien_llegado", activo=False)

    _aprobar(User.objects.all())

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [nuevo.email]


# --- El aviso ---

def test_aprobar_escribe_al_sindicato():
    sindicato = _sindicato(correo="sov.avila@ejemplo.es")

    _aprobar(User.objects.filter(pk=sindicato.pk))

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["sov.avila@ejemplo.es"]


def test_el_aviso_dice_el_usuario_y_por_donde_entrar():
    sindicato = _sindicato("sov_avila")

    _aprobar(User.objects.filter(pk=sindicato.pk))

    cuerpo = mail.outbox[0].body
    assert "sov_avila" in cuerpo, "sin el usuario no sabe con qué entrar"
    assert "/login/" in cuerpo, "y sin la dirección, adónde"


def test_cada_sindicato_recibe_su_propio_mensaje():
    """Nunca varios destinatarios en el mismo correo: eso enseñaría a cada
    sindicato la lista de los demás, que es una comunicación de datos a
    terceros que nadie ha autorizado."""
    _sindicato("uno", correo="uno@ejemplo.es")
    _sindicato("dos", correo="dos@ejemplo.es")

    _aprobar(User.objects.all())

    assert len(mail.outbox) == 2
    for mensaje in mail.outbox:
        assert len(mensaje.to) == 1
        assert not mensaje.cc
        assert not mensaje.bcc


# --- Que un problema con el correo no impida aprobar ---

def test_un_sindicato_sin_correo_se_aprueba_igual_y_se_avisa_al_admin():
    sin_correo = _sindicato("sin_correo", correo="")

    peticion = _aprobar(User.objects.filter(pk=sin_correo.pk))

    sin_correo.refresh_from_db()
    assert sin_correo.is_active is True, "la falta de correo no puede bloquear la aprobación"
    assert not mail.outbox
    textos = " ".join(str(m) for m in peticion._messages)
    assert "sin_correo" in textos, "hay que avisarle por otra vía, y saber a quién"


def test_un_fallo_del_servidor_de_correo_no_deshace_la_aprobacion(settings):
    """La aprobación es lo importante; el aviso es una cortesía. Al revés
    —quedarse sin aprobar porque el SMTP falló— sería peor."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    sindicato = _sindicato()

    from unittest.mock import patch
    with patch("gestion.admin.EmailMessage.send", side_effect=OSError("SMTP caido")):
        peticion = _aprobar(User.objects.filter(pk=sindicato.pk))

    sindicato.refresh_from_db()
    assert sindicato.is_active is True
    textos = " ".join(str(m) for m in peticion._messages)
    assert "no se ha podido avisar" in textos.lower()


# --- Auditoría ---

def test_aprobar_una_cuenta_queda_auditado(auditoria):
    """Aprobar salta el control manual de altas: es el único paso que separa a
    una cuenta cualquiera de poder subir datos de afiliación."""
    sindicato = _sindicato()

    _aprobar(User.objects.filter(pk=sindicato.pk))

    aprobaciones = [r for r in auditoria() if r["accion"] == ACCIONES.CUENTAS_APROBADAS]
    assert len(aprobaciones) == 1
    assert aprobaciones[0]["cantidad"] == 1


def test_la_auditoria_de_la_aprobacion_no_guarda_la_direccion(auditoria):
    _sindicato(correo="direccion.privada@ejemplo.es")

    _aprobar(User.objects.all())

    assert "direccion.privada" not in json.dumps(auditoria())
